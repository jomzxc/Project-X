from django import forms


class CSVUploadForm(forms.Form):
    file = forms.FileField(
        help_text="Upload CSV file with TOI data",
        widget=forms.ClearableFileInput(attrs={'accept': '.csv'})
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError("File must be a CSV")
        return file