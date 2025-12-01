import { 
  Task, 
  TaskFormData, 
  TaskStatusFilter,
  TaskFilter, 
  TaskStats, 
  TaskCreateData, 
  TaskUpdateData,
  TaskStatus,
  TaskAttachment,
  TaskNote,
  EmployeeReference
} from '../types';
import { api } from './api';

class TaskService {
  private baseUrl = '/api/tasks';

  async getTasks(filters?: TaskFilter): Promise<Task[]> {
    try {
      const response = await api.get<{ tasks?: Task[]; stats?: TaskStats; success?: boolean }>(
        `${this.baseUrl}/dashboard`,
        { params: filters }
      );
      if (response.data?.success === false) {
        console.warn('Task dashboard responded with error:', response.data);
        return [];
      }
      return Array.isArray(response.data?.tasks) ? response.data.tasks! : [];
    } catch (error) {
      console.error('Error fetching tasks:', error);
      return [];
    }
  }

  async getTaskById(id: string): Promise<Task> {
    try {
      const response = await api.get(`${this.baseUrl}/${id}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching task:', error);
      throw new Error('Failed to fetch task');
    }
  }

  async createTask(taskData: Partial<TaskCreateData>): Promise<{ success: boolean; task?: Task; error?: string }> {
    try {
      // Ensure task_description is used (backend expects this field)
      const payload: any = { ...taskData };
      if (payload.description && !payload.task_description) {
        payload.task_description = payload.description;
        delete payload.description;
      }
      
      console.log('📤 Creating task with payload:', payload);
      const response = await api.post(this.baseUrl, payload);
      console.log('✅ Task created successfully:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ Error creating task:', error);
      console.error('Error response:', error.response?.data);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to create task'
      };
    }
  }

  async updateTask(id: string, updateData: Partial<TaskUpdateData>): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.put(`${this.baseUrl}/${id}`, updateData);
      return response.data;
    } catch (error: any) {
      console.error('Error updating task:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to update task'
      };
    }
  }

  async deleteTask(id: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.delete(`${this.baseUrl}/${id}`);
      return response.data;
    } catch (error: any) {
      console.error('Error deleting task:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to delete task'
      };
    }
  }

  async getTaskStats(): Promise<TaskStats> {
    try {
      const response = await api.get(`${this.baseUrl}/stats`);
      return response.data;
    } catch (error) {
      console.error('Error fetching task stats:', error);
      // Return default stats if API fails
      return {
        total: 0,
        pending: 0,
        in_progress: 0,
        completed: 0,
        cancelled: 0,
        overdue: 0,
        waiting: 0,
        ai_suggested: 0,
        not_started: 0
      };
    }
  }

  async getMyTasks(): Promise<Task[]> {
    try {
      const response = await api.get(`${this.baseUrl}/my-tasks`);
      return response.data.tasks || [];
    } catch (error) {
      console.error('Error fetching my tasks:', error);
      return [];
    }
  }

  async getCollaborationTasks(): Promise<Task[]> {
    try {
      const response = await api.get<{ success: boolean; tasks?: Task[] }>(`${this.baseUrl}/collaboration`);
      if (response.data?.success && Array.isArray(response.data.tasks)) {
        return response.data.tasks;
      }
      return [];
    } catch (error) {
      console.error('Error fetching collaboration tasks:', error);
      return [];
    }
  }

  async assignTask(taskId: string, assigneeId: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.post(`${this.baseUrl}/${taskId}/assign`, { assignee_id: assigneeId });
      return response.data;
    } catch (error: any) {
      console.error('Error assigning task:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to assign task'
      };
    }
  }

  async updateTaskStatus(taskId: string, status: TaskStatus): Promise<{ success: boolean; error?: string }> {
    try {
      const updateData: Partial<TaskUpdateData> = { status };
      
      // If marking as completed, set completed_at
      if (status === 'completed') {
        updateData.completed_at = new Date().toISOString();
      }
      
      const response = await api.put(`${this.baseUrl}/${taskId}`, updateData);
      return response.data;
    } catch (error: any) {
      console.error('Error updating task status:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to update task status'
      };
    }
  }

  async addTaskComment(taskId: string, comment: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await api.post(`${this.baseUrl}/${taskId}/comments`, { comment });
      return response.data;
    } catch (error: any) {
      console.error('Error adding task comment:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to add comment'
      };
    }
  }

  async uploadTaskAttachment(taskId: string, file: File): Promise<{ success: boolean; attachment_url?: string; error?: string; message?: string }> {
    try {
      const formData = new FormData();
      formData.append('file', file); // Backend expects 'file' not 'attachment'
      
      console.log(`📤 Uploading file "${file.name}" to task ${taskId}`);
      const response = await api.post(`${this.baseUrl}/${taskId}/upload-file`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      if (response.data?.success) {
        console.log(`✅ File uploaded successfully:`, response.data);
      } else {
        console.warn('⚠️ Upload response indicates failure:', response.data);
      }
      
      return response.data;
    } catch (error: any) {
      console.error('❌ Error uploading task attachment:', error);
      console.error('Error details:', error.response?.data);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to upload attachment'
      };
    }
  }

  async getTaskAttachments(taskId: string): Promise<TaskAttachment[]> {
    try {
      const response = await api.get<{ success: boolean; attachments?: TaskAttachment[]; total?: number }>(
        `${this.baseUrl}/${taskId}/attachments`
      );
      if (response.data?.success === false) {
        console.warn('Task attachments API returned error:', response.data);
        return [];
      }
      const attachments = response.data.attachments ?? [];
      console.log(`✅ Loaded ${attachments.length} attachments for task ${taskId}`);
      return attachments;
    } catch (error) {
      console.error('Error fetching task attachments:', error);
      return [];
    }
  }

  async getTaskNotes(taskId: string): Promise<TaskNote[]> {
    try {
      const response = await api.get<{ success: boolean; notes?: TaskNote[] }>(
        `${this.baseUrl}/${taskId}/notes`
      );
      if (response.data?.success === false) {
        return [];
      }
      return response.data.notes ?? [];
    } catch (error) {
      console.error('Error fetching task notes:', error);
      return [];
    }
  }

  async addTaskNote(taskId: string, payload: { notes: string; progress?: number; attached_to?: string; attached_to_multiple?: string[] }): Promise<{ success: boolean; message?: string; error?: string }> {
    try {
      const sanitizedPayload = {
        ...payload,
        attached_to_multiple: payload.attached_to_multiple?.filter(Boolean),
      };
      if (!sanitizedPayload.attached_to_multiple?.length) {
        delete sanitizedPayload.attached_to_multiple;
      }
      if (!sanitizedPayload.attached_to) {
        delete sanitizedPayload.attached_to;
      }
      const response = await api.post(`${this.baseUrl}/${taskId}/add-note`, sanitizedPayload);
      return response.data;
    } catch (error: any) {
      console.error('Error adding task note:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to add note'
      };
    }
  }

  async getAvailableEmployeesForAttachment(taskId: string): Promise<{ success: boolean; employees?: EmployeeReference[]; total?: number; error?: string }> {
    try {
      const response = await api.get(`/api/tasks/${taskId}/available-employees`);
      return response.data;
    } catch (error: any) {
      console.error('Error fetching available employees for attachment:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to load employees',
        employees: [],
      };
    }
  }

  // Helper method to get tasks for dashboard
  async getDashboardTasks(userId?: string): Promise<{ recent: Task[]; overdue: Task[]; assigned: Task[] }> {
    try {
      // Get tasks with different filters for dashboard
      const [recentTasks, overdueTasks, assignedTasks] = await Promise.all([
        this.getTasks({ assigned_to: userId, status: 'all' }).then(tasks => 
          tasks.slice(0, 5).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        ),
        this.getTasks({ assigned_to: userId, status: 'pending' }).then(tasks =>
          tasks.filter(task => task.due_date && new Date(task.due_date) < new Date())
        ),
        this.getTasks({ assigned_to: userId, status: 'pending' }).then(tasks => tasks.slice(0, 10))
      ]);

      return {
        recent: recentTasks,
        overdue: overdueTasks,
        assigned: assignedTasks
      };
    } catch (error) {
      console.error('Error fetching dashboard tasks:', error);
      return {
        recent: [],
        overdue: [],
        assigned: []
      };
    }
  }

  // Helper method to calculate task statistics
  async calculateTaskStats(tasks: Task[]): Promise<TaskStats> {
    const now = new Date();
    
    const stats: TaskStats = {
      total: tasks.length,
      pending: tasks.filter(task => task.status === 'pending').length,
      in_progress: tasks.filter(task => task.status === 'in_progress').length,
      completed: tasks.filter(task => task.status === 'completed').length,
      cancelled: tasks.filter(task => task.status === 'cancelled').length,
      overdue: tasks.filter(task => 
        task.status !== 'completed' && 
        task.due_date && 
        new Date(task.due_date) < now
      ).length,
      waiting: tasks.filter(task => task.status === 'waiting').length,
      ai_suggested: tasks.filter(task => task.status === 'ai_suggested').length,
      not_started: tasks.filter(task => task.status === 'not_started').length
    };

    return stats;
  }

  async getTasksByStatus(status: TaskStatusFilter, userId?: string) {
    return this.getTasks({
      status: status === 'all' ? undefined : status,
      assigned_to: userId
    });
  }

  // Search tasks
  async searchTasks(query: string, filters?: TaskFilter): Promise<Task[]> {
    try {
      const response = await api.get(this.baseUrl, { 
        params: { ...filters, search: query } 
      });
      return response.data.tasks || [];
    } catch (error) {
      console.error('Error searching tasks:', error);
      return [];
    }
  }

  async generateTasksFromGoal(payload: {
    title: string;
    description?: string;
    output?: string;
    deadline?: string;
    department?: string;
    priority?: string;
    auto_classify?: boolean;
    template?: string;  // 🎯 ADD TEMPLATE PARAMETER
  }): Promise<{
    success: boolean;
    goal?: any;
    ai_tasks?: Task[];
    ai_breakdown?: any;
    ai_processing_time?: number;
    message?: string;
  }> {
    try {
      const response = await api.post('/api/tasks/goals/classify-only', payload);
      return response.data;
    } catch (error: any) {
      console.error('Error generating AI tasks:', error);
      return {
        success: false,
        message: error.response?.data?.error || 'Failed to generate tasks',
      };
    }
  }

  async generateRAGRecommendations(taskId: string): Promise<{
    success: boolean;
    ai_meta_id?: string;
    assignment_strategy?: string;
    is_predefined_process?: boolean;
    template?: string | null;
    recommended_role?: string | null;
    initial_activity?: string;
    initial_details?: string;
    error?: string;
  }> {
    try {
      const response = await api.post(`/api/tasks/${taskId}/generate-rag-recommendations`);
      return response.data;
    } catch (error: any) {
      console.error('Error generating RAG recommendations:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to generate RAG recommendations',
      };
    }
  }

  async getRAGRecommendationProgress(aiMetaId: string): Promise<{
    success: boolean;
    status?: string;
    progress?: number;
    current_activity?: string;
    output_json?: any;
    error?: string;
  }> {
    try {
      const response = await api.get(`/api/ai-meta/${aiMetaId}`);
      return response.data;
    } catch (error: any) {
      console.error('Error getting RAG progress:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to get RAG progress',
      };
    }
  }

  async getTaskEmployeeRecommendations(taskId: string): Promise<{
    success: boolean;
    recommendations?: any[];
    recommendations_available?: boolean;
    recommendations_generated_at?: string;
    error?: string;
  }> {
    try {
      const response = await api.get(`/api/tasks/${taskId}/employee-recommendations`);
      return response.data;
    } catch (error: any) {
      console.error('Error getting employee recommendations:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to get employee recommendations',
      };
    }
  }

  async applyEmployeeRecommendation(
    taskId: string,
    employeeId: string,
    recommendationData?: any
  ): Promise<{
    success: boolean;
    error?: string;
  }> {
    try {
      const response = await api.post(`/api/tasks/${taskId}/apply-employee-recommendation`, {
        employee_id: employeeId,
        recommendation_data: recommendationData,
      });
      return response.data;
    } catch (error: any) {
      console.error('Error applying recommendation:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to apply recommendation',
      };
    }
  }

  async getRAGRecommendationsStatus(objectiveId: string): Promise<{
    success: boolean;
    tasks?: Array<{
      task_id: string;
      task_description: string;
      status: 'completed' | 'in_progress' | 'pending' | 'failed';
      progress: number;
      current_activity: string;
      recommendations_count: number;
      ai_meta_id?: string;
      has_recommendations: boolean;
      error?: string;
    }>;
    summary?: {
      total_tasks: number;
      completed: number;
      in_progress: number;
      pending: number;
      failed: number;
    };
    error?: string;
  }> {
    try {
      const response = await api.get(`/api/objectives/${objectiveId}/rag-recommendations-status`);
      return response.data;
    } catch (error: any) {
      console.error('Error getting RAG recommendations status:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Failed to get RAG recommendations status',
      };
    }
  }
}

const taskService = new TaskService();

export { taskService };
export default taskService;