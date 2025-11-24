import React from 'react';
import { TaskManagement as TaskManagementComponent } from '../../components/TaskManagement/TaskManagement';
import './TaskManagement.css';

export const TaskManagement: React.FC = () => {
  return (
    <div className="shared-task-management">
      <TaskManagementComponent />
    </div>
  );
};

export default TaskManagement;