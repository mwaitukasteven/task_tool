from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from .models import Project, Task, Deadline, UserProfile
from .forms import ProjectForm, TaskForm, UserRegistrationForm, UserProfileForm
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

def homepage(request):
    """View for the main homepage that shows different content based on authentication status."""
    if request.user.is_authenticated:
        # Get statistics for authenticated users
        total_projects = Project.objects.filter(user=request.user).count()
        completed_projects = Project.objects.filter(user=request.user, status='completed').count()
        active_projects = Project.objects.filter(user=request.user, status='in_progress').count()
        total_tasks = Task.objects.filter(project__user=request.user).count()
        
        # Get recent projects and tasks
        recent_projects = Project.objects.filter(user=request.user).order_by('-created_at')[:5]
        recent_tasks = Task.objects.filter(project__user=request.user).order_by('-created_at')[:5]
        
        context = {
            'total_projects': total_projects,
            'completed_projects': completed_projects,
            'active_projects': active_projects,
            'total_tasks': total_tasks,
            'recent_projects': recent_projects,
            'recent_tasks': recent_tasks,
        }
    else:
        context = {}
    
    return render(request, 'homepage.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def home(request):
    user = request.user
    total_projects = Project.objects.filter(user=user).count()
    completed_projects = Project.objects.filter(user=user, status='completed').count()
    active_projects = Project.objects.filter(user=user, status='in_progress').count()
    total_tasks = Task.objects.filter(project__user=user).count()
    
    recent_projects = Project.objects.filter(user=user).order_by('-created_at')[:5]
    recent_tasks = Task.objects.filter(project__user=user).order_by('-created_at')[:5]
    
    context = {
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'active_projects': active_projects,
        'total_tasks': total_tasks,
        'recent_projects': recent_projects,
        'recent_tasks': recent_tasks,
    }
    return render(request, 'task_manager_app/home.html', context)

@login_required
def project_list(request):
    projects = Project.objects.filter(user=request.user).annotate(
        completed_tasks_count=Count('tasks', filter=Q(tasks__is_completed=True))
    ).order_by('-created_at')
    return render(request, 'task_manager_app/project_list.html', {'projects': projects})

@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            messages.success(request, 'Project created successfully!')
            return redirect('task_manager:dashboard')
    else:
        form = ProjectForm()
    return render(request, 'task_manager_app/project_form.html', {'form': form})

@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    tasks = project.tasks.all()
    
    # Calculate completion percentage
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(is_completed=True).count()
    completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    return render(request, 'task_manager_app/project_detail.html', {
        'project': project,
        'tasks': tasks,
        'completion_percentage': completion_percentage,
        'completed_tasks_count': completed_tasks,
    })

@login_required
def task_create(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()
            return redirect('task_manager:project_detail', project_id=project.id)
    else:
        form = TaskForm()
    return render(request, 'task_manager_app/task_form.html', {'form': form, 'project': project})

@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk, project__owner=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully!')
            return redirect('task_manager:project_detail', pk=task.project.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, 'task_manager_app/task_form.html', {'form': form, 'project': task.project})

@login_required
def task_toggle_complete(request, task_id):
    task = get_object_or_404(Task, id=task_id, project__user=request.user)
    task.is_completed = not task.is_completed
    task.save()
    return redirect('task_manager:project_detail', project_id=task.project.id)

@login_required
def profile(request):
    user = request.user
    user_profile = UserProfile.objects.get(user=user)
    
    # Get user's projects
    projects = Project.objects.filter(user=user)
    total_projects = projects.count()
    completed_projects = projects.filter(status='completed').count()
    active_projects = projects.filter(status='in_progress').count()
    
    # Get user's tasks
    tasks = Task.objects.filter(project__user=user)
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(is_completed=True).count()
    pending_tasks = tasks.filter(is_completed=False).count()
    
    # Get recent activity
    recent_projects = projects.order_by('-updated_at')[:5]
    recent_tasks = tasks.order_by('-updated_at')[:5]
    
    context = {
        'user_profile': user_profile,
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'active_projects': active_projects,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'recent_projects': recent_projects,
        'recent_tasks': recent_tasks,
    }
    
    return render(request, 'task_manager_app/profile.html', context)

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('task_manager:homepage')

@login_required
def project_edit(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('task_manager:project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'task_manager_app/project_form.html', {'form': form, 'project': project})

@login_required
def project_delete(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)
    if request.method == 'POST':
        project.delete()
        return redirect('task_manager:project_list')
    return render(request, 'task_manager_app/project_confirm_delete.html', {'project': project})

@login_required
def task_list(request):
    tasks = Task.objects.filter(project__user=request.user).order_by('-created_at')
    return render(request, 'task_manager_app/task_list.html', {'tasks': tasks})

@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id, project__user=request.user)
    return render(request, 'task_manager_app/task_detail.html', {
        'task': task,
        'project': task.project
    })

@login_required
def task_edit(request, task_id):
    task = get_object_or_404(Task, id=task_id, project__user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('task_manager:project_detail', project_id=task.project.id)
    else:
        form = TaskForm(instance=task)
    return render(request, 'task_manager_app/task_form.html', {'form': form, 'task': task, 'project': task.project})

@login_required
def task_delete(request, task_id):
    task = get_object_or_404(Task, id=task_id, project__user=request.user)
    if request.method == 'POST':
        project_id = task.project.id
        task.delete()
        return redirect('task_manager:project_detail', project_id=project_id)
    return render(request, 'task_manager_app/task_confirm_delete.html', {'task': task})

@login_required
def dashboard(request):
    """View for the authenticated user's dashboard."""
    # Get statistics
    total_projects = Project.objects.filter(user=request.user).count()
    completed_projects = Project.objects.filter(user=request.user, status='completed').count()
    active_projects = Project.objects.filter(user=request.user, status='in_progress').count()
    total_tasks = Task.objects.filter(project__user=request.user).count()
    
    # Get recent projects and tasks
    recent_projects = Project.objects.filter(user=request.user).order_by('-created_at')[:5]
    recent_tasks = Task.objects.filter(project__user=request.user).order_by('-created_at')[:5]
    
    context = {
        'total_projects': total_projects,
        'completed_projects': completed_projects,
        'active_projects': active_projects,
        'total_tasks': total_tasks,
        'recent_projects': recent_projects,
        'recent_tasks': recent_tasks,
    }
    
    return render(request, 'task_manager_app/dashboard.html', context)

@login_required
def profile_edit(request):
    """View for editing user profile."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('task_manager:profile')
    else:
        form = UserProfileForm(instance=request.user.userprofile)
    
    return render(request, 'task_manager_app/profile_edit.html', {'form': form})
