import pandas as pd
import uuid
import json

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

from .forms import CSVUploadForm
from .models import ClassificationJob, TOIResult
from .ml_pipeline import classifier


def upload_view(request):
    """Handle CSV upload and display form."""
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            job_id = str(uuid.uuid4())[:8]
            file_name_to_save = uploaded_file.name

            file_path = default_storage.save(f"uploads/{job_id}_{file_name_to_save}", uploaded_file)

            try:
                df = pd.read_csv(default_storage.path(file_path), comment='#', skip_blank_lines=True,
                                 on_bad_lines='skip', low_memory=False)

                job = ClassificationJob.objects.create(
                    job_id=job_id,
                    status='PROCESSING',
                    total_objects=len(df),
                    file_path=file_path,
                    file_name=file_name_to_save
                )

                results = classifier.predict_batch(df)
                result_objects = []
                for i, result in enumerate(results):
                    # Helper function to find IDs from various possible column names
                    def get_id_from_row(row, potential_names, default_prefix=None):
                        for name in potential_names:
                            if name in row and pd.notna(row[name]):
                                return row[name]
                        # Only create a default if a prefix is provided
                        if default_prefix:
                            return f'{default_prefix}-{i + 1}'
                        return None  # Return None if no match and no default

                    row_data = df.iloc[i]

                    toi_id = get_id_from_row(row_data, ['toi_id', 'toi', 'TOI'], 'TOI')
                    tic_id = get_id_from_row(row_data,
                                             ['tid', 'tic_id', 'tic', 'TIC', 'TIC ID'])

                    result_objects.append(
                        TOIResult(
                            job=job,
                            toi_id=str(toi_id),
                            tic_id=str(tic_id) if tic_id is not None else None,
                            prediction=result['prediction'],
                            probability=result['probability'],
                            confidence=result['confidence'],
                            feature_data=json.dumps(row_data.to_dict())
                        )
                    )

                TOIResult.objects.bulk_create(result_objects, batch_size=1000)
                job.status = 'COMPLETED'
                job.processed_objects = len(results)
                job.save()
                return redirect('results', job_id=job_id)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
    else:
        form = CSVUploadForm()
    return render(request, 'classifier/upload.html', {'form': form})


def job_history_view(request):
    """Display a paginated list of all classification jobs."""
    job_list = ClassificationJob.objects.all().order_by('-created_at')
    paginator = Paginator(job_list, 10)
    page_number = request.GET.get('page')
    jobs = paginator.get_page(page_number)
    return render(request, 'classifier/job_history.html', {'jobs': jobs})


def results_view(request, job_id):
    """Display classification results with pagination and filtering."""
    job = get_object_or_404(ClassificationJob, job_id=job_id)
    results_list = job.results.all().order_by('id')

    confidence_filter = request.GET.get('confidence', '')
    prediction_filter = request.GET.get('prediction', '')
    prob_min_filter = request.GET.get('prob_min', '')
    prob_max_filter = request.GET.get('prob_max', '')

    if confidence_filter: results_list = results_list.filter(confidence=confidence_filter)
    if prediction_filter: results_list = results_list.filter(prediction=prediction_filter)
    if prob_min_filter:
        try:
            results_list = results_list.filter(probability__gte=float(prob_min_filter))
        except (ValueError, TypeError):
            pass
    if prob_max_filter:
        try:
            results_list = results_list.filter(probability__lte=float(prob_max_filter))
        except (ValueError, TypeError):
            pass

    total_results = job.results.all().count()
    planet_count = job.results.filter(prediction='Planet').count()
    paginator = Paginator(results_list, 15)
    page_number = request.GET.get('page')
    results_page = paginator.get_page(page_number)

    filter_params = request.GET.copy()
    if 'page' in filter_params: del filter_params['page']

    context = {
        'job': job,
        'results_page': results_page,
        'total_results': total_results,
        'planet_count': planet_count,
        'fp_count': total_results - planet_count,
        'high_conf_count': job.results.filter(confidence='High').count(),
        'planet_percentage': (planet_count / total_results * 100) if total_results > 0 else 0,
        'filters': {'confidence': confidence_filter, 'prediction': prediction_filter, 'prob_min': prob_min_filter,
                    'prob_max': prob_max_filter},
        'filter_params': filter_params.urlencode(),
    }
    return render(request, 'classifier/results.html', context)


@csrf_exempt
def api_classify_single(request):
    """API endpoint for single TOI classification."""
    if request.method == 'POST':
        try:
            df = pd.DataFrame([json.loads(request.body)])
            return JsonResponse(classifier.predict_batch(df)[0])
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST required'}, status=405)


def download_results_csv(request, job_id):
    """Download results as CSV, now including TIC ID."""
    job = get_object_or_404(ClassificationJob, job_id=job_id)
    results = job.results.values_list('toi_id', 'tic_id', 'prediction', 'probability', 'confidence')
    df = pd.DataFrame(results, columns=['toi_id', 'tic_id', 'prediction', 'probability', 'confidence'])
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="tess_results_{job.file_name}_{job.id}.csv"'
    df.to_csv(path_or_buf=response, index=False)
    return response


@require_POST
def delete_job_view(request, job_id):
    """Deletes a job, its results, and the associated CSV file."""
    job_to_delete = get_object_or_404(ClassificationJob, job_id=job_id)

    # 1. Delete the physical file from storage
    if job_to_delete.file_path and default_storage.exists(job_to_delete.file_path):
        default_storage.delete(job_to_delete.file_path)

    # 2. Delete the job record from the database
    # (Related TOIResult objects will be cascade-deleted automatically)
    job_to_delete.delete()

    # 3. Add a success message for the user
    messages.success(request, f"Successfully deleted Job #{job_id}.")

    # 4. Redirect back to the job history page
    return redirect('job_history')

def notebook_view(request):
    """Renders the page that will display the Jupyter Notebook."""
    return render(request, 'notebooks/notebook.html')