import React from 'react';
import { Task } from '../../types';
import { Button } from '../Common/UI/Button';

interface TaskListProps {
  tasks: Task[];
  onEditTask: (task: Task) => void;
  onDeleteTask: (taskId: string) => void;
  onStatusChange: (taskId: string, status: Task['status']) => void;
}

const statusLabels: Record<Task['status'], string> = {
  pending: 'Pending',
  in_progress: 'In Progress',
  completed: 'Completed',
  cancelled: 'Cancelled',
  waiting: 'Waiting',
  ai_suggested: 'AI Suggested',
  not_started: 'Not Started'
};

const statusOptions: Task['status'][] = [
  'pending',
  'in_progress',
  'completed',
  'cancelled',
  'waiting',
  'not_started',
  'ai_suggested'
];

export const TaskList: React.FC<TaskListProps> = ({
  tasks,
  onEditTask,
  onDeleteTask,
  onStatusChange
}) => {
  if (tasks.length === 0) {
    return (
      <div className="task-list empty">
        <p>No tasks found. Try adjusting your filters or create a new task.</p>
      </div>
    );
  }

  return (
    <div className="task-list">
      <table>
        <thead>
          <tr>
            <th>Task</th>
            <th>Strategic Objective</th>
            <th>Pre Number</th>
            <th>Assigned Date</th>
            <th>Status</th>
            <th>Priority</th>
            <th>Assignee</th>
            <th>Due Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map(task => (
            <tr key={task.id}>
              <td>
                <div className="task-title">
                  <strong>{task.title}</strong>
                  <p>{task.description}</p>
                </div>
              </td>
              <td>{task.strategic_objective || task.objectives?.title || '—'}</td>
              <td>{task.pre_number || task.objectives?.pre_number || '—'}</td>
              <td>{task.assigned_at ? new Date(task.assigned_at).toLocaleDateString() : 'N/A'}</td>
              <td>
                <select
                  value={task.status}
                  onChange={(e) => onStatusChange(task.id, e.target.value as Task['status'])}
                >
                  {statusOptions.map(status => (
                    <option key={status} value={status}>
                      {statusLabels[status]}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <span className={`priority-badge ${task.priority}`}>
                  {task.priority.toUpperCase()}
                </span>
              </td>
              <td>{task.assigned_to_name || task.assigned_to}</td>
              <td>{task.due_date ? new Date(task.due_date).toLocaleDateString() : 'N/A'}</td>
              <td className="task-actions">
                <Button variant="secondary" size="small" onClick={() => onEditTask(task)}>
                  ✏️ Edit
                </Button>
                <Button variant="danger" size="small" onClick={() => onDeleteTask(task.id)}>
                  🗑️ Delete
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TaskList;

