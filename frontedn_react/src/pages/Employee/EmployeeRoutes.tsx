import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Profile from './Profile';
import ChangePassword from './ChangePassword';
import TaskManagement from './TaskManagement';
import TaskDetailPage from './TaskDetailPage';
import Notifications from './Notifications';
import TaskResponsePortal from './TaskResponsePortal';

const EmployeeRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="profile" element={<Profile />} />
      <Route path="change-password" element={<ChangePassword />} />
      <Route path="task-management" element={<TaskManagement />} />
      <Route path="task-management/:taskId" element={<TaskDetailPage />} />
      <Route path="notifications" element={<Notifications />} />
      <Route path="respond/:taskId" element={<TaskResponsePortal />} />
      <Route path="*" element={<Profile />} />
    </Routes>
  );
};

export default EmployeeRoutes;