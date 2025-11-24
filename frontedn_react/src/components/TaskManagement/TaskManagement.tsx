import React, { useState, useEffect, useMemo } from 'react';
import { Task, TaskFilter } from '../../types';
import { taskService } from '../../services/task';
import { TaskList } from './TaskList';
import { TaskForm } from './TaskForm';
import { TaskFilters } from './TaskFilters';
import { Button } from '../Common/UI/Button';
import { TaskManagementFilters } from './types';
import './TaskManagement.css';

const defaultFilters: TaskManagementFilters = {
  status: 'all',
  priority: 'all',
  assigned_to: 'all',
  search: ''
};

export const TaskManagement: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [filters, setFilters] = useState<TaskManagementFilters>(defaultFilters);

  useEffect(() => {
    loadTasks();
  }, [filters.status, filters.priority, filters.assigned_to]);

  const displayedTasks = useMemo(() => {
    if (!filters.search) return tasks;
    const query = filters.search.toLowerCase();
    return tasks.filter(task =>
      task.title.toLowerCase().includes(query) ||
      task.description.toLowerCase().includes(query) ||
      task.assigned_to_name?.toLowerCase().includes(query) ||
      task.assigned_to.toLowerCase().includes(query)
    );
  }, [tasks, filters.search]);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError('');
      const apiFilters: TaskFilter = {};
      if (filters.status !== 'all') {
        apiFilters.status = filters.status;
      }
      if (filters.priority !== 'all') {
        apiFilters.priority = filters.priority;
      }
      if (filters.assigned_to !== 'all') {
        apiFilters.assigned_to = filters.assigned_to;
      }

      const data = await taskService.getTasks(apiFilters);
      setTasks(data);
    } catch (err) {
      setError('Failed to load tasks');
      console.error('Error loading tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = () => {
    setEditingTask(null);
    setShowForm(true);
  };

  const handleEditTask = (task: Task) => {
    setEditingTask(task);
    setShowForm(true);
  };

  const handleSaveTask = async (taskData: Partial<Task>) => {
    try {
      setError('');
      if (editingTask) {
          const result = await taskService.updateTask(editingTask.id, taskData);
          if (!result.success) {
            throw new Error(result.error || 'Failed to update task');
          }
      } else {
          const result = await taskService.createTask(taskData);
          if (!result.success) {
            throw new Error(result.error || 'Failed to create task');
          }
      }

      setShowForm(false);
      setEditingTask(null);
      await loadTasks();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Error ${editingTask ? 'updating' : 'creating'} task: ${message}`);
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (window.confirm('Are you sure you want to delete this task?')) {
      try {
        const result = await taskService.deleteTask(taskId);
        if (!result.success) {
          throw new Error(result.error || 'Failed to delete task');
        }
        await loadTasks();
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(`Error deleting task: ${message}`);
      }
    }
  };

  const handleStatusChange = async (taskId: string, newStatus: Task['status']) => {
    try {
      const result = await taskService.updateTaskStatus(taskId, newStatus);
      if (!result.success) {
        throw new Error(result.error || 'Failed to update task status');
      }
      await loadTasks();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Error updating task status: ${message}`);
    }
  };

  const handleFiltersChange = (updatedFilters: Partial<TaskManagementFilters>) => {
    setFilters(prev => ({
      ...prev,
      ...updatedFilters
    }));
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingTask(null);
  };

  if (loading) {
    return <div className="loading">Loading tasks...</div>;
  }

  return (
    <div className="task-management">
      <div className="task-management-header">
        <h2>📋 Task Management</h2>
        <Button variant="primary" onClick={handleCreateTask}>
          ➕ Create New Task
        </Button>
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError('')} className="btn-close">×</button>
        </div>
      )}

      <TaskFilters
        filters={filters}
        onFiltersChange={handleFiltersChange}
        tasks={tasks}
      />

      <TaskList
        tasks={displayedTasks}
        onEditTask={handleEditTask}
        onDeleteTask={handleDeleteTask}
        onStatusChange={handleStatusChange}
      />

      {showForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <TaskForm
              task={editingTask}
              onSave={handleSaveTask}
              onCancel={handleCloseForm}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskManagement;