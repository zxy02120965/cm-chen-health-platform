import { createRouter, createWebHistory } from 'vue-router'
import PatientLayout from '../layouts/PatientLayout.vue'
import PatientHome from '../pages/patient/PatientHome.vue'
import PatientProfile from '../pages/patient/PatientProfile.vue'
import PatientArchive from '../pages/patient/PatientArchive.vue'
import PatientAssessment from '../pages/patient/PatientAssessment.vue'
import PatientAssessmentResult from '../pages/patient/PatientAssessmentResult.vue'
import PatientPlan from '../pages/patient/PatientPlan.vue'
import PatientRecords from '../pages/patient/PatientRecords.vue'
import PatientKnowledge from '../pages/patient/PatientKnowledge.vue'
import PatientKnowledgeDetail from '../pages/patient/PatientKnowledgeDetail.vue'
import PatientConsult from '../pages/patient/PatientConsult.vue'
import PatientServices from '../pages/patient/PatientServices.vue'
import PatientMedicalFiles from '../pages/patient/PatientMedicalFiles.vue'
import PatientBodyRecord from '../pages/patient/PatientBodyRecord.vue'
import PatientDietRecord from '../pages/patient/PatientDietRecord.vue'
import PatientExerciseRecord from '../pages/patient/PatientExerciseRecord.vue'
import PatientPulmonaryRecord from '../pages/patient/PatientPulmonaryRecord.vue'
import PatientTrend from '../pages/patient/PatientTrend.vue'
import CareLayout from '../layouts/CareLayout.vue'
import CareDashboard from '../pages/care/CareDashboard.vue'
import CarePatients from '../pages/care/CarePatients.vue'
import CarePatient360 from '../pages/care/CarePatient360.vue'
import CareTodos from '../pages/care/CareTodos.vue'
import CareSettings from '../pages/care/CareSettings.vue'
import CareConsults from '../pages/care/CareConsults.vue'
import CareAlerts from '../pages/care/CareAlerts.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/patient/home' },
    {
      path: '/patient', component: PatientLayout,
      children: [
        { path: 'home', component: PatientHome, meta: { nav: 'home' } },
        { path: 'profile', component: PatientProfile, meta: { nav: 'home' } },
        { path: 'archive', component: PatientArchive, meta: { nav: 'archive' } },
        { path: 'archive/:sectionId', component: PatientAssessment, meta: { nav: 'archive' } },
        { path: 'assessment/result', component: PatientAssessmentResult, meta: { nav: 'archive' } },
        { path: 'medical-files', component: PatientMedicalFiles, meta: { nav: 'archive' } },
        { path: 'plan', component: PatientPlan, meta: { nav: 'plan' } },
        { path: 'records', component: PatientRecords, meta: { nav: 'records' } },
        { path: 'records/body', component: PatientBodyRecord, meta: { nav: 'records' } },
        { path: 'records/diet', component: PatientDietRecord, meta: { nav: 'records' } },
        { path: 'records/exercise', component: PatientExerciseRecord, meta: { nav: 'records' } },
        { path: 'records/pulmonary', component: PatientPulmonaryRecord, meta: { nav: 'records' } },
        { path: 'records/trend', component: PatientTrend, meta: { nav: 'records' } },
        { path: 'knowledge', component: PatientKnowledge, meta: { nav: 'home' } },
        { path: 'knowledge/:id', component: PatientKnowledgeDetail, meta: { nav: 'home' } },
        { path: 'consult', component: PatientConsult, meta: { nav: 'home' } },
        { path: 'services', component: PatientServices, meta: { nav: 'home' } },
      ],
    },
    { path: '/care', component: CareLayout, children: [
      { path: 'dashboard', component: CareDashboard, meta: { careNav: 'dashboard' } },
      { path: 'patients', component: CarePatients, meta: { careNav: 'patients' } },
      { path: 'patients/:id', component: CarePatient360, meta: { careNav: 'patients' } },
      { path: 'todos', component: CareTodos, meta: { careNav: 'todos' } },
      { path: 'assessments', redirect: '/care/todos?tab=assessment-review' },
      { path: 'plans', redirect: '/care/todos?tab=plan-review' },
      { path: 'alerts', component: CareAlerts, meta: { careNav: 'alerts' } },
      { path: 'consults', component: CareConsults, meta: { careNav: 'consults' } },
      { path: 'education', redirect: '/care/settings?tab=education' },
      { path: 'settings', component: CareSettings, meta: { careNav: 'settings' } },
    ] },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router
