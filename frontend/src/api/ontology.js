import { api } from './base'

export const listCategories = () => api.get('/ontology/categories')
export const getCategory = (categoryId) => api.get(`/ontology/categories/${categoryId}`)
export const createCategory = (payload) => api.post('/ontology/categories', payload)
export const updateCategory = (categoryId, payload) =>
  api.patch(`/ontology/categories/${categoryId}`, payload)
export const deleteCategory = (categoryId) => api.delete(`/ontology/categories/${categoryId}`)

export const listCompetencies = () => api.get('/ontology/competencies')
export const getCompetency = (competencyId) => api.get(`/ontology/competencies/${competencyId}`)
export const createCompetency = (payload) => api.post('/ontology/competencies', payload)
export const updateCompetency = (competencyId, payload) =>
  api.patch(`/ontology/competencies/${competencyId}`, payload)
export const deleteCompetency = (competencyId) =>
  api.delete(`/ontology/competencies/${competencyId}`)

export const listSubCompetencies = () => api.get('/ontology/sub-competencies')
export const getSubCompetency = (subCompetencyId) =>
  api.get(`/ontology/sub-competencies/${subCompetencyId}`)
export const createSubCompetency = (payload) =>
  api.post('/ontology/sub-competencies', payload)
export const updateSubCompetency = (subCompetencyId, payload) =>
  api.patch(`/ontology/sub-competencies/${subCompetencyId}`, payload)
export const deleteSubCompetency = (subCompetencyId) =>
  api.delete(`/ontology/sub-competencies/${subCompetencyId}`)
