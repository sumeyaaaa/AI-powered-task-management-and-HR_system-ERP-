import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Dashboard from './Dashboard';
import EmployeeManagement from './EmployeeManagement';
import TaskManagement from './TaskManagement';
import Notifications from './Notifications';
import TaskDetailPage from './TaskDetailPage';

const AdminRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="dashboard" element={<Dashboard />} />
      <Route path="employee-management" element={<EmployeeManagement />} />
      <Route path="task-management" element={<TaskManagement />} />
      <Route path="task-management/:taskId" element={<TaskDetailPage />} />
      <Route path="notifications" element={<Notifications />} />
      <Route path="*" element={<Dashboard />} />
    </Routes>
  );
};

export default AdminRoutes;