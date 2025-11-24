import React, { useMemo } from 'react';
import { Task } from '../../types';
import { TaskManagementFilters } from './types';

interface TaskFiltersProps {
  filters: TaskManagementFilters;
  onFiltersChange: (updates: Partial<TaskManagementFilters>) => void;
  tasks: Task[];
}

const statusOptions: Array<{ label: string; value: Task['status'] | 'all' }> = [
  { label: 'All Statuses', value: 'all' },
  { label: 'Pending', value: 'pending' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Completed', value: 'completed' },
  { label: 'Cancelled', value: 'cancelled' },
  { label: 'Waiting', value: 'waiting' },
  { label: 'Not Started', value: 'not_started' },
  { label: 'AI Suggested', value: 'ai_suggested' }
];

const priorityOptions: Array<{ label: string; value: Task['priority'] | 'all' }> = [
  { label: 'All Priorities', value: 'all' },
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' },
  { label: 'Urgent', value: 'urgent' }
];

export const TaskFilters: React.FC<TaskFiltersProps> = ({
  filters,
  onFiltersChange,
  tasks
}) => {
  const assigneeOptions = useMemo(() => {
    const map = new Map<string, string>();
    tasks.forEach(task => {
      if (task.assigned_to) {
        map.set(task.assigned_to, task.assigned_to_name || task.assigned_to);
      }
    });

    return [
      { id: 'all', name: 'All Assignees' },
      ...Array.from(map.entries()).map(([id, name]) => ({ id, name }))
    ];
  }, [tasks]);

  return (
    <div className="task-filters">
      <div className="filter-group">
        <label htmlFor="search">Search</label>
        <input
          id="search"
          type="text"
          placeholder="Search by title, description, assignee..."
          value={filters.search}
          onChange={(e) => onFiltersChange({ search: e.target.value })}
        />
      </div>

      <div className="filter-group">
        <label htmlFor="status">Status</label>
        <select
          id="status"
          value={filters.status}
          onChange={(e) => onFiltersChange({ status: e.target.value as Task['status'] | 'all' })}
        >
          {statusOptions.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="priority">Priority</label>
        <select
          id="priority"
          value={filters.priority}
          onChange={(e) => onFiltersChange({ priority: e.target.value as Task['priority'] | 'all' })}
        >
          {priorityOptions.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="assignee">Assignee</label>
        <select
          id="assignee"
          value={filters.assigned_to}
          onChange={(e) => onFiltersChange({ assigned_to: e.target.value })}
        >
          {assigneeOptions.map(option => (
            <option key={option.id} value={option.id}>
              {option.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default TaskFilters;

