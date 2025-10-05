import joblib
import numpy as np
import pandas as pd
import os
from django.conf import settings
import json


class TESSClassifier:
    def __init__(self):
        self.model = None
        self.feature_names = None
        self.feature_medians = {}
        self.load_model()

    def load_model(self):
        """Load the trained Gradient Boosting model and metadata."""
        model_dir = os.path.join(settings.BASE_DIR, 'models')
        try:
            self.model = joblib.load(os.path.join(model_dir, 'best_model.pkl'))
            self.feature_names = joblib.load(os.path.join(model_dir, 'feature_names.pkl'))

            metadata_path = os.path.join(model_dir, 'model_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    self.feature_medians = metadata.get('feature_medians', {})
        except Exception as e:
            print(f"Error loading model: {e}")
            raise

    def preprocess_features(self, df):
        """Preprocess features with median imputation and Winsorization."""
        df_processed = df.copy()
        for col in self.feature_names:
            if col in df_processed.columns:
                col_median = self.feature_medians.get(col, df_processed[col].median())
                if pd.isna(col_median):
                    col_median = 0.0
                df_processed[col] = df_processed[col].fillna(col_median)

                Q1 = df_processed[col].quantile(0.25)
                Q3 = df_processed[col].quantile(0.75)
                IQR = Q3 - Q1
                if not pd.isna(IQR) and IQR > 0:
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    df_processed[col] = np.clip(df_processed[col], lower_bound, upper_bound)
        return df_processed

    def predict_batch(self, df):
        """Predict classifications for a batch of data."""
        X = pd.DataFrame(columns=self.feature_names)
        for feature in self.feature_names:
            if feature in df.columns:
                X[feature] = df[feature]

        X_processed = self.preprocess_features(X)
        X_processed = X_processed.fillna(0)

        predictions = self.model.predict(X_processed)
        probabilities = self.model.predict_proba(X_processed)[:, 1]

        results = []
        for pred, prob in zip(predictions, probabilities):
            if abs(prob - 0.5) > 0.4:
                confidence = 'High'
            elif abs(prob - 0.5) > 0.2:
                confidence = 'Medium'
            else:
                confidence = 'Low'

            results.append({
                'prediction': 'Planet' if pred == 1 else 'False Positive',
                'probability': float(prob),
                'confidence': confidence,
            })
        return results


classifier = TESSClassifier()