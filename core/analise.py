import os
import json
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    precision_recall_curve, roc_curve, auc, f1_score, precision_score, recall_score
)
from sklearn.model_selection import cross_val_score
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class AdvancedMovementAnalyzer:
    """
    Sistema avançado de análise para modelos One-Class com métricas completas
    """

    def __init__(self, model_path: str, data_path: str):
        self.model_path = model_path
        self.data_path = data_path
        self.results = {}
        self._load_model()

    def _load_model(self):
        """Carregamento robusto do modelo com validação"""
        try:
            model_data = joblib.load(self.model_path)

            if isinstance(model_data, dict):
                self.model = model_data['model']
                self.features = model_data.get('features', [])
                self.scaler = model_data.get('scaler')
                self.model_metadata = model_data.get('metadata', {})
                print(
                    f"✅ Modelo carregado: {self.model_metadata.get('model_name', 'Unknown')}")
            else:
                self.model = model_data
                self.features = []
                self.scaler = None
                self.model_metadata = {}
                print("⚠️ Modelo carregado sem metadados")

        except Exception as e:
            raise ValueError(f"Erro ao carregar modelo: {e}")

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engenharia de features avançada"""
        # Features base
        numeric_features = [
            col for col in df.columns
            if col not in ["exercise", "label", "timestamp", "frame_num", "video_file"]
            and not col.endswith('_missing')
            and pd.api.types.is_numeric_dtype(df[col])
        ]

        X = df[numeric_features].copy()

        # Reordena features se disponível
        if self.features:
            available_features = [f for f in self.features if f in X.columns]
            missing_features = set(self.features) - set(available_features)

            if missing_features:
                print(
                    f"⚠️ {len(missing_features)} features faltando: {list(missing_features)[:5]}")

            X = X.reindex(columns=available_features, fill_value=0)

        # Engenharia de features temporal
        if 'timestamp' in df.columns:
            X['movement_velocity'] = self._calculate_velocity(df)
            X['acceleration'] = self._calculate_acceleration(df)

        return X

    def _calculate_velocity(self, df: pd.DataFrame) -> pd.Series:
        """Calcula velocidade do movimento"""
        if 'LEFT_HIP_y' in df.columns and 'timestamp' in df.columns:
            hip_positions = df['LEFT_HIP_y'].diff() / df['timestamp'].diff()
            return hip_positions.fillna(0)
        return pd.Series(0, index=df.index)

    def _calculate_acceleration(self, df: pd.DataFrame) -> pd.Series:
        """Calcula aceleração do movimento"""
        velocity = self._calculate_velocity(df)
        acceleration = velocity.diff() / df['timestamp'].diff()
        return acceleration.fillna(0)

    def comprehensive_evaluation(self, output_dir: str = "advanced_results") -> Dict:
        """Avaliação abrangente do modelo"""
        os.makedirs(output_dir, exist_ok=True)

        # Carrega dados
        df_test = pd.read_parquet(self.data_path, engine='pyarrow')
        print(f"📊 Dados carregados: {len(df_test)} registros")

        # Análise exploratória
        self._exploratory_analysis(df_test, output_dir)

        # Prepara dados
        X_test = self._engineer_features(df_test)
        y_true = df_test.get('label', pd.Series(
            1, index=df_test.index))  # Fallback

        # Predições
        if hasattr(self.model, 'decision_function'):
            y_scores = self.model.decision_function(X_test)
            y_pred = self.model.predict(X_test)
        else:
            y_scores = self.model.predict_proba(X_test)[:, 1] if hasattr(
                self.model, 'predict_proba') else self.model.predict(X_test)
            y_pred = self.model.predict(X_test)

        # Converte para formato binário
        y_pred_binary = np.where(y_pred == -1, 0, 1)

        # Métricas avançadas
        metrics = self._calculate_advanced_metrics(
            y_true, y_pred_binary, y_scores)

        # Visualizações
        self._generate_advanced_visualizations(
            y_true, y_pred_binary, y_scores, output_dir)

        # Salva resultados
        self._save_detailed_results(metrics, output_dir)

        return metrics

    def _calculate_advanced_metrics(self, y_true, y_pred, y_scores) -> Dict:
        """Calcula métricas avançadas de performance"""
        return {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1_score': f1_score(y_true, y_pred, zero_division=0),
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist(),
            'classification_report': classification_report(y_true, y_pred, output_dict=True),
            'roc_auc': self._calculate_roc_auc(y_true, y_scores) if len(np.unique(y_scores)) > 1 else 0,
            'precision_recall_auc': self._calculate_precision_recall_auc(y_true, y_scores)
        }

    def _calculate_roc_auc(self, y_true, y_scores) -> float:
        """Calcula AUC-ROC com tratamento de erros"""
        try:
            fpr, tpr, _ = roc_curve(y_true, y_scores)
            return auc(fpr, tpr)
        except:
            return 0.0

    def _calculate_precision_recall_auc(self, y_true, y_scores) -> float:
        """Calcula AUC Precision-Recall"""
        try:
            precision, recall, _ = precision_recall_curve(y_true, y_scores)
            return auc(recall, precision)
        except:
            return 0.0

    def _exploratory_analysis(self, df: pd.DataFrame, output_dir: str):
        """Análise exploratória dos dados"""
        # Estatísticas descritivas
        desc_stats = df.describe().round(3)
        desc_stats.to_csv(os.path.join(
            output_dir, "descriptive_statistics.csv"))

        # Distribuição de classes
        plt.figure(figsize=(10, 6))
        df['label'].value_counts().plot(kind='bar')
        plt.title('Distribuição das Classes')
        plt.savefig(os.path.join(output_dir, "class_distribution.png"))
        plt.close()

    def _generate_advanced_visualizations(self, y_true, y_pred, y_scores, output_dir: str):
        """Gera visualizações avançadas"""
        # Matriz de confusão
        plt.figure(figsize=(8, 6))
        cm = confusion_matrix(y_true, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title('Matriz de Confusão')
        plt.savefig(os.path.join(output_dir, "confusion_matrix.png"))
        plt.close()

        # Curva ROC
        if len(np.unique(y_scores)) > 1:
            fpr, tpr, _ = roc_curve(y_true, y_scores)
            roc_auc = auc(fpr, tpr)

            plt.figure(figsize=(8, 6))
            plt.plot(fpr, tpr, label=f'ROC curve (AUC = {roc_auc:.2f})')
            plt.plot([0, 1], [0, 1], 'k--')
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')
            plt.title('Curva ROC')
            plt.legend()
            plt.savefig(os.path.join(output_dir, "roc_curve.png"))
            plt.close()

    def _save_detailed_results(self, metrics: Dict, output_dir: str):
        """Salva resultados detalhados"""
        # Salva métricas
        with open(os.path.join(output_dir, "detailed_metrics.json"), 'w') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        # Relatório executivo
        report = {
            'model_performance_summary': {
                'accuracy': f"{metrics['accuracy']:.4f}",
                'f1_score': f"{metrics['f1_score']:.4f}",
                'roc_auc': f"{metrics.get('roc_auc', 0):.4f}",
                'model_type': str(type(self.model)),
                'timestamp': pd.Timestamp.now().isoformat()
            },
            'recommendations': self._generate_recommendations(metrics)
        }

        with open(os.path.join(output_dir, "executive_report.json"), 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Gera recomendações baseadas nas métricas"""
        recommendations = []

        if metrics['accuracy'] < 0.8:
            recommendations.append(
                "🎯 Considere ajustar hiperparâmetros do modelo")

        if metrics['f1_score'] < 0.7:
            recommendations.append(
                "🎯 Balanceamento de classes pode melhorar F1-Score")

        if metrics.get('roc_auc', 0) < 0.8:
            recommendations.append(
                "🎯 Avalie feature engineering para melhor discriminação")

        return recommendations


# Compatibilidade com API anterior
class OneClassModelEvaluator:
    """
    Wrapper compatível com a API antiga para avaliação one-class.
    Usa internamente AdvancedMovementAnalyzer.
    """

    def __init__(self, model_path: str, data_path: str):
        self._delegate = AdvancedMovementAnalyzer(model_path, data_path)

    def evaluate(self, output_dir: str = "results_oneclass") -> Dict:
        return self._delegate.comprehensive_evaluation(output_dir)


def evaluate_oneclass_model(model_path: str, data_path: str,
                            output_dir: str = "results_oneclass") -> Dict:
    """Função auxiliar compatível com API antiga."""
    evaluator = OneClassModelEvaluator(model_path, data_path)
    return evaluator.evaluate(output_dir)
