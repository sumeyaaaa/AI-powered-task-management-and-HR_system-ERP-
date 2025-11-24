import { Task } from '../../types';

export type TaskManagementFilters = {
  status: Task['status'] | 'all';
  priority: Task['priority'] | 'all';
  assigned_to: string | 'all';
  search: string;
};

