import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink],
  template: `
    <div class="container">
      <nav class="card" style="display:flex; gap:12px; align-items:center;">
        <a routerLink="/tasks">Tasks</a>
      </nav>
      <router-outlet></router-outlet>
    </div>
  `
})
export class AppShellComponent {}
