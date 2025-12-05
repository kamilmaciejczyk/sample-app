export interface Task {
  id?: number;
  title: string;
  description?: string;
  dueDate?: string; // ISO date string (yyyy-MM-dd)
  completed: boolean;
  createdAt?: string;
  updatedAt?: string;
}
