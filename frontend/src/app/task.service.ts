import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Task } from './task.model';

@Injectable({ providedIn: 'root' })
export class TaskService {
  private readonly base = '/api/tasks';
  constructor(private http: HttpClient) {}
  list(): Observable<Task[]> { return this.http.get<Task[]>(this.base); }
  create(task: Task): Observable<Task> { return this.http.post<Task>(this.base, task); }
  update(id: number, task: Task): Observable<Task> { return this.http.put<Task>(`${this.base}/${id}`, task); }
  delete(id: number): Observable<void> { return this.http.delete<void>(`${this.base}/${id}`); }
}
