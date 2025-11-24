import React from 'react';
import { EmployeeForm } from './EmployeeForm';

interface AddEmployeeFormProps {
  onSave: () => void;
  onBack: () => void;
}

export const AddEmployeeForm: React.FC<AddEmployeeFormProps> = ({ onSave, onBack }) => {
  return (
    <div className="add-employee-form">
      <EmployeeForm
        mode="create"
        onSave={onSave}
        onCancel={onBack}
      />
    </div>
  );
};

export default AddEmployeeForm;

