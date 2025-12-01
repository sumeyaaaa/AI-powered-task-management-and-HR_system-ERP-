export type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'waiting'
  | 'ai_suggested'
  | 'not_started';

export type TaskStatusFilter = TaskStatus | 'all';

export interface Objective {
  id?: string;
  title?: string;
  pre_number?: string;
  priority?: string;
  description?: string;
  output?: string;
  deadline?: string;
  department?: string;
  auto_classify?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface EmployeeReference {
  id?: string;
  name?: string;
  email?: string;
  role?: string;
  department?: string;
}

export interface StrategicAnalysis {
  context?: string;
  objective?: string;
  process?: string;
  delivery?: string;
  reporting_requirements?: string;
  validation_score?: number;
  q4_execution_context?: string;
  process_applied?: string;
  goal_type?: string;
}

export interface EmployeeRecommendation {
  employee_id: string;
  employee_name: string;
  employee_role?: string;
  employee_department?: string;
  fit_score: number;
  confidence?: 'high' | 'medium' | 'low';
  reason?: string;
  key_qualifications?: string[];
  skills_match?: any;
  skills_match_list?: string[];
  rag_enhanced?: boolean;
  rag_enhanced_score?: number;
  role_based_assignment?: boolean;
  assignment_type?: 'direct_role_assignment' | 'analysis';
}

export interface StrategicMetadata {
  context?: string;
  objective?: string;
  objective_number?: string;
  process?: string;
  delivery?: string;
  reporting_requirements?: string;
  strategic_analysis?: string | StrategicAnalysis;
  assigned_role?: string;
  recommended_role?: string;  // 🎯 For predefined processes
  employee_recommendations_available?: boolean;
  recommendations_failed?: boolean;
  recommendations_generated_at?: string;
  rag_enhanced?: boolean;
  employees_with_jd?: number;
  ai_recommendations?: EmployeeRecommendation[];
  recommendations_analysis?: string;
  total_employees_considered?: number;
  complexity?: 'low' | 'medium' | 'high';
  required_skills?: string[];
  success_criteria?: string;
  validation_score?: number;
  q4_execution_context?: string;
  process_applied?: string;
  goal_type?: string;
  predefined_process?: boolean;  // 🎯 Flag for predefined processes
  assignment_strategy?: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  task_description?: string;
  status: TaskStatus;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  assigned_to: string;
  assigned_to_name?: string;
  assigned_to_multiple?: string[];
  created_by: string;
  created_by_name?: string;
  due_date: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  assigned_at?: string;
  tags?: string[];
  attachments?: string[];
  estimated_hours?: number;
  actual_hours?: number;
  completion_percentage?: number;
  progress?: number;
  objective_id?: string;
  objectives?: Objective;
  dependencies?: string[];
  strategic_metadata?: StrategicMetadata;
  employees?: EmployeeReference;
  ai_suggested?: boolean;
  strategic_objective?: string;
  pre_number?: string;
}

export interface TaskFormData {
  title: string;
  description: string;
  status: TaskStatus;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  assigned_to: string;
  assigned_to_multiple?: string[];
  due_date: string;
  tags?: string[];
  estimated_hours?: number;
  objective_id?: string;
  dependencies?: string[];
}

export interface TaskCreateData extends TaskFormData {
  created_by: string;
}

export interface TaskUpdateData extends Partial<TaskFormData> {
  id: string;
  actual_hours?: number;
  completed_at?: string;
  completion_percentage?: number;
  ai_suggested?: boolean;
  assigned_at?: string;
  strategic_metadata?: Partial<StrategicMetadata>;
}

export interface TaskFilter {
  status?: TaskStatusFilter;
  priority?: string;
  assigned_to?: string;
  created_by?: string;
  due_date_from?: string;
  due_date_to?: string;
  objective_id?: string;
  assignment?: 'All' | 'Assigned' | 'Unassigned';
  employee_filter?: string;
  priority_filter?: string;
  objective_filter?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
}

export interface TaskStats {
  total: number;
  completed: number;
  pending: number;
  in_progress: number;
  cancelled: number;
  overdue: number;
  waiting: number;
  ai_suggested: number;
  not_started: number;
  completed_tasks?: number;
  pending_tasks?: number;
  in_progress_tasks?: number;
  overdue_tasks?: number;
  total_tasks?: number;
}

export interface TaskDashboard {
  stats: TaskStats;
  tasks: Task[];
  recent_tasks?: Task[];
}

export interface Goal {
  id: string;
  title: string;
  description?: string;
  output?: string;
  deadline: string;
  department?: string;
  priority: 'low' | 'medium' | 'high';
  auto_classify?: boolean;
  pre_number?: string;
  created_at?: string;
  updated_at?: string;
  ai_tasks?: Task[];
  ai_breakdown?: string;
}

export interface GoalFormData {
  title: string;
  description: string;
  output: string;
  deadline: string;
  department: string;
  priority: 'low' | 'medium' | 'high';
  auto_classify: boolean;
}

export interface AIGoalResult {
  success: boolean;
  ai_meta_id?: string;
  ai_processing_time?: number;
  ai_tasks?: Task[];
  ai_breakdown?: string;
  rag_enhanced?: boolean;
  error?: string;
}

export interface TaskAttachment {
  id?: string;
  task_id?: string;
  filename?: string;
  file_name?: string;
  file_type?: string;
  file_url?: string;
  file_size?: number;
  public_url?: string;
  employee_id?: string;
  employee_name?: string;
  uploaded_by?: string;
  uploaded_by_name?: string;
  notes?: string;
  created_at?: string;
  update_id?: string;
}

export interface TaskNote {
  id: string;
  task_id?: string;
  employee_id?: string;
  employee_name?: string;
  employee_role?: string;
  notes: string;
  progress?: number;
  attached_to?: string;
  attached_to_name?: string;
  attached_to_multiple?: string[];
  attached_to_multiple_names?: string[];
  has_attachments?: boolean;
  attachments_count?: number;
  attachments?: TaskAttachment[];
  created_at?: string;
  updated_at?: string;
  updated_by?: string;
  is_attached_to_me?: boolean;
}

export interface Notification {
  id: string;
  message: string;
  type:
    | 'info'
    | 'success'
    | 'warning'
    | 'error'
    | 'task_assigned'
    | 'task_updated'
    | 'file_uploaded'
    | 'note_added';
  is_read: boolean;
  meta?: {
    task_id?: string;
    task_description?: string;
    assigned_by?: string;
    note_preview?: string;
    file_name?: string;
  };
  created_at: string;
  read_at?: string;
}

export interface EmployeeRecommendationResponse {
  success: boolean;
  recommendations?: EmployeeRecommendation[];
  recommendations_available?: boolean;
  error?: string;
}

export interface RAGRecommendationResponse {
  success: boolean;
  ai_meta_id?: string;
  status?: 'processing' | 'completed' | 'error';
  progress?: number;
  current_activity?: string;
  error?: string;
}

export interface TaskServiceResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  tasks?: Task[];
  task?: Task;
  goals?: Goal[];
  goal?: Goal;
  stats?: TaskStats;
  dashboard?: TaskDashboard;
  notes?: TaskNote[];
  attachments?: TaskAttachment[];
  total?: number;
  unread_count?: number;
  notifications?: Notification[];
  available_dependencies?: Task[];
  available_employees?: EmployeeReference[];
}

export interface TaskActionState {
  show_approve_form: boolean;
  show_edit_form: boolean;
  show_recommendations: boolean;
  rag_loading: boolean;
  rag_ai_meta_id?: string;
  selected_recommendation?: EmployeeRecommendation;
  approved: boolean;
  editing?: boolean;
  status?: string;
  priority?: string;
  progress?: number;
}

export interface TaskFilterOptions {
  status: string;
  assignment: string;
  employee_filter: string;
  priority_filter: string;
  objective_filter: string;
  sort_by: string;
  start_date?: Date;
  end_date?: Date;
}

export interface TaskProposal {
  title: string;
  description: string;
  detailed_description: string;
  priority: 'low' | 'medium' | 'high';
  due_date: string;
  goal_id?: string;
  assign_suggestion: string;
  estimated_hours?: number;
}

export interface TaskComment {
  id: string;
  task_id: string;
  user_id: string;
  user_name: string;
  comment: string;
  created_at: string;
  updated_at: string;
}
 