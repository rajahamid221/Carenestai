import json
import os
from datetime import datetime, timedelta
import random

class AICarePlanner:
    def __init__(self):
        # Load clinical guidelines
        self.guidelines = self._load_clinical_guidelines()
        
    def _load_clinical_guidelines(self):
        """Load clinical guidelines from JSON file"""
        guidelines_path = os.path.join('static', 'data', 'clinical_guidelines.json')
        try:
            with open(guidelines_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default guidelines if file not found
            return {
                'diabetes': {
                    'goals': ['Blood glucose control', 'Weight management', 'Physical activity'],
                    'interventions': ['Regular blood glucose monitoring', 'Dietary counseling', 'Exercise program']
                },
                'hypertension': {
                    'goals': ['Blood pressure control', 'Lifestyle modification', 'Medication adherence'],
                    'interventions': ['Regular BP monitoring', 'Salt reduction', 'Stress management']
                }
            }

    def _generate_ai_insights(self, patient_data):
        """Generate AI insights based on patient data"""
        diagnosis = patient_data.get('diagnosis', '').lower()
        age = patient_data.get('age', 0)
        medical_history = patient_data.get('medical_history', '')
        
        # Generate personalized insights based on patient data
        insights = []
        
        # Age-based recommendations
        if age > 65:
            insights.append("Consider geriatric-specific care considerations and fall prevention strategies.")
        elif age < 18:
            insights.append("Focus on growth and development monitoring, with age-appropriate activities.")
        
        # Diagnosis-specific insights
        if 'diabetes' in diagnosis.lower():
            insights.append("Regular monitoring of blood glucose levels and HbA1c is essential.")
            insights.append("Consider dietary modifications and regular exercise program.")
        elif 'hypertension' in diagnosis.lower():
            insights.append("Regular blood pressure monitoring and stress management are key.")
            insights.append("Consider salt reduction and regular physical activity.")
        
        # Medical history-based insights
        if 'heart' in medical_history.lower():
            insights.append("Regular cardiac monitoring and exercise tolerance assessment recommended.")
        if 'lung' in medical_history.lower():
            insights.append("Pulmonary function monitoring and breathing exercises may be beneficial.")
        
        # Combine insights into a coherent text
        return "\n".join([
            "AI-Generated Care Plan Insights:",
            "Based on the patient's profile and medical history, the following considerations are recommended:",
            *insights,
            "\nRegular follow-up and monitoring of progress is essential.",
            "Adjust care plan based on patient's response and changing needs."
        ])

    def _create_structured_care_plan(self, patient_data, ai_insights):
        """Create a structured care plan from AI insights"""
        diagnosis = patient_data.get('diagnosis', '').lower()
        
        # Get relevant guidelines for the diagnosis
        diagnosis_guidelines = self.guidelines.get(diagnosis, self.guidelines.get('default', {}))
        
        # Calculate target dates
        start_date = datetime.now()
        end_date = start_date + timedelta(days=90)  # 3-month care plan
        
        # Create structured care plan
        care_plan = {
            'title': f"AI-Generated Care Plan for {patient_data.get('diagnosis')}",
            'diagnosis': patient_data.get('diagnosis'),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'goals': [],
            'interventions': [],
            'notes': ai_insights,
            'status': 'active'
        }
        
        # Add goals from guidelines
        for goal in diagnosis_guidelines.get('goals', []):
            care_plan['goals'].append({
                'title': goal,
                'description': f"AI-recommended goal: {goal}",
                'target_date': (start_date + timedelta(days=30)).strftime('%Y-%m-%d'),
                'status': 'pending'
            })
        
        # Add interventions from guidelines
        for intervention in diagnosis_guidelines.get('interventions', []):
            care_plan['interventions'].append({
                'title': intervention,
                'description': f"AI-recommended intervention: {intervention}",
                'frequency': 'daily',
                'status': 'pending'
            })
        
        return care_plan

    def generate_care_plan(self, patient_data):
        """Generate a personalized care plan for a patient"""
        # Generate AI insights
        ai_insights = self._generate_ai_insights(patient_data)
        
        # Create structured care plan
        care_plan = self._create_structured_care_plan(patient_data, ai_insights)
        
        return care_plan

    def update_care_plan(self, existing_care_plan, new_patient_data):
        """Update an existing care plan based on new patient data"""
        # Generate new insights
        new_insights = self._generate_ai_insights(new_patient_data)
        
        # Update care plan with new insights
        updated_care_plan = existing_care_plan.copy()
        updated_care_plan['notes'] = new_insights
        
        # Update goals and interventions based on new data
        for goal in updated_care_plan['goals']:
            if goal['status'] == 'pending':
                goal['status'] = 'in_progress'
        
        return updated_care_plan 