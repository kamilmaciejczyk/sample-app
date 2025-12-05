import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TaskService } from './task.service';
import { Task } from './task.model';

@Component({
  selector: 'tm-tasks',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html'
})
export class AppComponent {
  tasks = signal<Task[]>([]);
  loading = signal<boolean>(false);
  error = signal<string>('');

  newTitle = '';
  newDescription = '';
  newDueDate = '';

  constructor(private api: TaskService) {
    this.refresh();
  }

  refresh() {
    this.loading.set(true);
    this.api.list().subscribe({
      next: (data) => { this.tasks.set(data); this.loading.set(false); },
      error: (e) => { this.error.set('Cannot load tasks'); this.loading.set(false); console.error(e); }
    });
  }

  add() {
    if (!this.newTitle.trim()) return;
    const task: Task = { title: this.newTitle.trim(), description: this.newDescription || undefined, dueDate: this.newDueDate || undefined, completed: false };
    this.api.create(task).subscribe({ next: () => { this.newTitle=''; this.newDescription=''; this.newDueDate=''; this.refresh(); } });
  }

  toggle(task: Task) {
    if (!task.id) return;
    const updated: Task = { ...task, completed: !task.completed };
    this.api.update(task.id, updated).subscribe({ next: () => this.refresh() });
  }

  remove(task: Task) {
    if (!task.id) return;
    this.api.delete(task.id).subscribe({ next: () => this.refresh() });
  }
}
