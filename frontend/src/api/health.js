import { api } from './base';

export const healthCheck = () => api.get('/health');
