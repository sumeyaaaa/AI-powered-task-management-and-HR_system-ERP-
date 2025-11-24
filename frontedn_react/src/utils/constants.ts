export const config = {
    BACKEND_URL: process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000',
  };
  
  export const ROLES = {
    SUPERADMIN: 'superadmin',
    EMPLOYEE: 'employee',
  } as const;