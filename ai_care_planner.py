import json
import os
from datetime import datetime, timedelta
import random

class AICarePlanner:
    def __init__(self):
        self.clinical_guidelines = self._load_clinical_guidelines()

    def generate_care_plan(self, patient_data):
        """Generate a comprehensive, personalized care plan based on patient data"""
        ai_insights = self._generate_ai_insights(patient_data)
        return self._create_structured_care_plan(patient_data, ai_insights)

    def update_care_plan(self, existing_care_plan, patient_data):
        """Update existing care plan based on new patient data and progress"""
        ai_insights = self._generate_ai_insights(patient_data)
        updated_plan = self._create_structured_care_plan(patient_data, ai_insights)
        
        # Preserve existing progress and status
        for goal in updated_plan['goals']:
            for existing_goal in existing_care_plan['goals']:
                if goal['title'] == existing_goal['title']:
                    goal['status'] = existing_goal['status']
                    goal['progress'] = existing_goal.get('progress', 0)
        
        for intervention in updated_plan['interventions']:
            for existing_intervention in existing_care_plan['interventions']:
                if intervention['title'] == existing_intervention['title']:
                    intervention['status'] = existing_intervention['status']
                    intervention['last_performed'] = existing_intervention.get('last_performed')
        
        return updated_plan

    def _load_clinical_guidelines(self):
        """Load comprehensive clinical guidelines from JSON file"""
        guidelines_path = os.path.join('static', 'data', 'clinical_guidelines.json')
        try:
            with open(guidelines_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'diabetes': {
                    'risk_factors': ['age', 'family_history', 'obesity', 'physical_inactivity'],
                    'goals': [
                        {
                            'title': 'Blood Glucose Control',
                            'target': 'Maintain HbA1c < 7%',
                            'frequency': 'Quarterly',
                            'interventions': [
                                'Regular blood glucose monitoring',
                                'HbA1c testing every 3 months',
                                'Medication adherence tracking'
                            ]
                        },
                        {
                            'title': 'Weight Management',
                            'target': 'Achieve and maintain BMI < 25',
                            'frequency': 'Monthly',
                            'interventions': [
                                'Nutritional counseling',
                                'Physical activity program',
                                'Weight monitoring'
                            ]
                        }
                    ],
                    'interventions': [
                        {
                            'title': 'Blood Glucose Monitoring',
                            'frequency': 'Daily',
                            'details': 'Monitor fasting and post-prandial glucose levels',
                            'equipment': 'Glucometer',
                            'education': 'Proper technique and timing of measurements'
                        },
                        {
                            'title': 'Dietary Management',
                            'frequency': 'Daily',
                            'details': 'Follow diabetic diet plan',
                            'education': 'Carbohydrate counting and meal planning'
                        }
                    ]
                },
                'hypertension': {
                    'risk_factors': ['age', 'family_history', 'obesity', 'high_salt_diet'],
                    'goals': [
                        {
                            'title': 'Blood Pressure Control',
                            'target': 'Maintain BP < 140/90 mmHg',
                            'frequency': 'Weekly',
                            'interventions': [
                                'Regular BP monitoring',
                                'Medication adherence',
                                'Lifestyle modifications'
                            ]
                        },
                        {
                            'title': 'Lifestyle Modification',
                            'target': 'Implement DASH diet and regular exercise',
                            'frequency': 'Daily',
                            'interventions': [
                                'Dietary counseling',
                                'Exercise program',
                                'Stress management'
                            ]
                        }
                    ],
                    'interventions': [
                        {
                            'title': 'Blood Pressure Monitoring',
                            'frequency': 'Daily',
                            'details': 'Monitor BP at consistent times',
                            'equipment': 'Home BP monitor',
                            'education': 'Proper measurement technique'
                        },
                        {
                            'title': 'Lifestyle Management',
                            'frequency': 'Daily',
                            'details': 'Implement DASH diet and exercise routine',
                            'education': 'Dietary guidelines and exercise recommendations'
                        }
                    ]
                }
            }

    def _generate_ai_insights(self, patient_data):
        """Generate comprehensive AI insights based on patient data"""
        diagnosis = patient_data.get('diagnosis', '').lower()
        age = patient_data.get('age', 0)
        medical_history = patient_data.get('medical_history', '')
        risk_factors = patient_data.get('risk_factors', [])
        
        insights = []
        
        # Risk Assessment
        risk_level = self._assess_risk_level(patient_data)
        insights.append(f"Risk Level Assessment: {risk_level}")
        
        # Age-specific considerations
        if age > 65:
            insights.extend([
                "Geriatric Considerations:",
                "- Regular fall risk assessment",
                "- Medication review for polypharmacy",
                "- Cognitive function monitoring",
                "- Social support assessment"
            ])
        elif age < 18:
            insights.extend([
                "Pediatric Considerations:",
                "- Growth and development monitoring",
                "- Age-appropriate activity planning",
                "- Family education and support",
                "- School integration if needed"
            ])
        
        # Diagnosis-specific insights
        if 'diabetes' in diagnosis.lower():
            insights.extend([
                "Diabetes Management Focus:",
                "- Regular HbA1c monitoring (target < 7%)",
                "- Foot care assessment and education",
                "- Eye examination schedule",
                "- Kidney function monitoring"
            ])
        elif 'hypertension' in diagnosis.lower():
            insights.extend([
                "Hypertension Management Focus:",
                "- Regular BP monitoring (target < 140/90 mmHg)",
                "- Salt reduction education",
                "- Stress management techniques",
                "- Regular exercise program"
            ])
        
        # Comorbidity considerations
        if 'heart' in medical_history.lower():
            insights.extend([
                "Cardiac Considerations:",
                "- Regular cardiac monitoring",
                "- Exercise tolerance assessment",
                "- Medication interaction review",
                "- Cardiac rehabilitation if indicated"
            ])
        if 'lung' in medical_history.lower():
            insights.extend([
                "Pulmonary Considerations:",
                "- Pulmonary function monitoring",
                "- Breathing exercise program",
                "- Air quality awareness",
                "- Vaccination status review"
            ])
        
        # Risk factor management
        if risk_factors:
            insights.append("\nRisk Factor Management:")
            for factor in risk_factors:
                insights.append(f"- {factor}: Implement specific management strategies")
        
        # Combine insights into a coherent text
        return "\n".join([
            "AI-Generated Care Plan Insights:",
            "Based on comprehensive patient assessment, the following considerations are recommended:",
            *insights,
            "\nMonitoring and Follow-up:",
            "- Regular progress assessment",
            "- Care plan adjustment based on response",
            "- Patient education and self-management support",
            "- Interdisciplinary team coordination as needed"
        ])

    def _assess_risk_level(self, patient_data):
        """Assess patient risk level based on various factors"""
        risk_score = 0
        
        # Age-based risk
        age = patient_data.get('age', 0)
        if age > 65:
            risk_score += 2
        elif age > 50:
            risk_score += 1
        
        # Comorbidity risk
        medical_history = patient_data.get('medical_history', '').lower()
        if any(condition in medical_history for condition in ['heart', 'lung', 'kidney', 'liver']):
            risk_score += 2
        
        # Risk factors
        risk_factors = patient_data.get('risk_factors', [])
        risk_score += len(risk_factors)
        
        # Determine risk level
        if risk_score >= 4:
            return "High Risk - Requires intensive monitoring and frequent follow-up"
        elif risk_score >= 2:
            return "Moderate Risk - Regular monitoring and follow-up needed"
        else:
            return "Low Risk - Standard monitoring and follow-up"

    def _create_structured_care_plan(self, patient_data, ai_insights):
        """Create a comprehensive, structured care plan"""
        diagnosis = patient_data.get('diagnosis', '').lower()
        diagnoses = [d.strip() for d in diagnosis.split(',') if d.strip()]
        
        # Merge guidelines for all diagnoses
        merged_guidelines = {'goals': [], 'interventions': []}
        for diag in diagnoses:
            diag_guidelines = self.clinical_guidelines.get(diag, self.clinical_guidelines.get('default', {}))
            merged_guidelines['goals'].extend(diag_guidelines.get('goals', []))
            merged_guidelines['interventions'].extend(diag_guidelines.get('interventions', []))
        
        # Add extra interventions for constipation
        if 'constipation' in diagnosis:
            merged_guidelines['goals'].append({
                'title': 'Bowel Regularity',
                'target': 'Maintain regular bowel movements',
                'frequency': 'Daily',
                'interventions': [
                    'Increase dietary fiber',
                    'Adequate hydration',
                    'Physical activity',
                    'Medication review for constipating drugs'
                ]
            })
            merged_guidelines['interventions'].append({
                'title': 'Constipation Management',
                'frequency': 'Daily',
                'details': 'Monitor bowel movements, increase fiber and fluids, encourage mobility',
                'equipment': 'N/A',
                'education': 'Educate on high-fiber foods, hydration, and when to seek help'
            })
        
        # Calculate target dates
        start_date = datetime.now()
        end_date = start_date + timedelta(days=90)  # 3-month care plan
        
        # Create structured care plan
        care_plan = {
            'title': f"Comprehensive Care Plan for {patient_data.get('diagnosis')}",
            'diagnosis': patient_data.get('diagnosis'),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'risk_level': self._assess_risk_level(patient_data),
            'goals': [],
            'interventions': [],
            'notes': ai_insights,
            'status': 'active',
            'monitoring_schedule': self._create_monitoring_schedule(patient_data)
        }
        
        # Add structured goals (deduplicated by title)
        seen_goal_titles = set()
        for goal in merged_guidelines.get('goals', []):
            if goal['title'] not in seen_goal_titles:
                care_plan['goals'].append({
                    'title': goal['title'],
                    'target': goal['target'],
                    'description': f"SMART Goal: {goal['title']} - {goal['target']}",
                    'frequency': goal['frequency'],
                    'target_date': (start_date + timedelta(days=30)).strftime('%Y-%m-%d'),
                    'status': 'pending',
                    'progress': 0,
                    'interventions': goal['interventions']
                })
                seen_goal_titles.add(goal['title'])
        
        # Add detailed interventions with description
        for intervention in merged_guidelines.get('interventions', []):
            description = f"{intervention.get('details', '')}"
            if intervention.get('education'):
                description += f" Education: {intervention['education']}"
            if intervention.get('equipment') and intervention.get('equipment') != 'N/A':
                description += f" Equipment: {intervention['equipment']}"
            care_plan['interventions'].append({
                'title': intervention['title'],
                'frequency': intervention['frequency'],
                'details': intervention['details'],
                'equipment': intervention.get('equipment', 'N/A'),
                'education': intervention['education'],
                'description': description.strip(),
                'status': 'pending',
                'last_performed': None
            })
        
        return care_plan

    def _create_monitoring_schedule(self, patient_data):
        """Create a detailed monitoring schedule based on patient needs"""
        diagnosis = patient_data.get('diagnosis', '').lower()
        risk_level = self._assess_risk_level(patient_data)
        
        schedule = {
            'vital_signs': {
                'frequency': 'Daily' if 'High Risk' in risk_level else 'Weekly',
                'parameters': ['Blood Pressure', 'Heart Rate', 'Temperature', 'Weight']
            },
            'lab_tests': {
                'frequency': 'Monthly' if 'High Risk' in risk_level else 'Quarterly',
                'tests': []
            },
            'follow_up': {
                'frequency': 'Weekly' if 'High Risk' in risk_level else 'Monthly',
                'type': 'In-person or Telehealth'
            }
        }
        
        # Add diagnosis-specific monitoring
        if 'diabetes' in diagnosis.lower():
            schedule['lab_tests']['tests'].extend([
                'HbA1c',
                'Fasting Blood Glucose',
                'Kidney Function',
                'Lipid Profile'
            ])
        elif 'hypertension' in diagnosis.lower():
            schedule['lab_tests']['tests'].extend([
                'Complete Blood Count',
                'Kidney Function',
                'Electrolytes',
                'Lipid Profile'
            ])
        
        return schedule
