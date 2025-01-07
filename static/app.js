// Global state
let projects = [];
let tasks = [];
let calendar = null;

// Function to load projects
async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        if (!response.ok) {
            throw new Error('Failed to load projects');
        }
        projects = await response.json();
        displayProjects();
        // After loading projects, load tasks since they depend on project data
        await loadTasks();
    } catch (error) {
        console.error('Error loading projects:', error);
        showToast('error', 'Failed to load projects');
    }
}

// Function to load tasks
async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        if (!response.ok) {
            throw new Error('Failed to load tasks');
        }
        tasks = await response.json();
        displayTasks();
    } catch (error) {
        console.error('Error loading tasks:', error);
        showToast('error', 'Failed to load tasks');
    }
}

// Initialize event handlers
document.addEventListener('DOMContentLoaded', function() {
    // Load projects first, which will then load tasks
    loadProjects();
    
    // Initialize calendar
    initializeCalendar();
    
    loadBackups();
    
    // Add event listeners to buttons
    const analyzeTasksBtn = document.getElementById('analyzeTasksBtn');
    if (analyzeTasksBtn) {
        console.log('Adding click listener to analyze tasks button');
        analyzeTasksBtn.removeAttribute('onclick');
        analyzeTasksBtn.addEventListener('click', analyzeTasks);
    }

    const generateStatusReportBtn = document.getElementById('generateStatusReportBtn');
    if (generateStatusReportBtn) {
        generateStatusReportBtn.removeAttribute('onclick');
        generateStatusReportBtn.addEventListener('click', generateStatusReport);
    }

    const scheduleTasksBtn = document.getElementById('scheduleTasksBtn');
    if (scheduleTasksBtn) {
        scheduleTasksBtn.removeAttribute('onclick');
        scheduleTasksBtn.addEventListener('click', generateSchedule);
    }

    // Add event listener for task save button
    const addTaskModalSaveBtn = document.getElementById('addTaskModalSaveBtn');
    if (addTaskModalSaveBtn) {
        console.log('Adding click listener to task save button');
        addTaskModalSaveBtn.addEventListener('click', async function() {
            const taskId = document.getElementById('taskId').value;
            if (taskId) {
                // If we have a task ID, this is an edit
                await updateTask(taskId);
            } else {
                // Otherwise, this is a new task
                await addTask();
            }
        });
    }

    // Add event listeners to buttons
    const deleteEventBtn = document.getElementById('deleteEventBtn');
    if (deleteEventBtn) {
        console.log('Adding click listener to delete event button');
        deleteEventBtn.addEventListener('click', async function() {
            try {
                if (!currentEventId) {
                    throw new Error('No event selected for deletion');
                }

                const event = calendar.getEventById(currentEventId);
                console.log('Found event:', event);

                if (!event) {
                    throw new Error('Event not found');
                }

                // Delete from backend first
                const response = await fetch(`/api/calendar/${currentEventId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to delete event');
                }

                // If backend deletion was successful, remove from calendar
                event.remove();
                
                // Close the modal
                const modal = document.getElementById('addEventModal');
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
                
                showToast('success', 'Event deleted successfully');
            } catch (error) {
                console.error('Error deleting event:', error);
                showToast('error', error.message || 'Failed to delete event');
            }
        });
    }

    // Add event listener for delete button clicks
    document.addEventListener('click', function(event) {
        if (event.target.matches('#deleteEventBtn')) {
            const eventId = event.target.getAttribute('data-event-id');
            if (eventId) {
                deleteEvent(eventId);
            }
        }
    });

    // Initialize backup modal
    const backupBtn = document.querySelector('button[data-action="backup"]');
    if (backupBtn) {
        backupBtn.onclick = function() {
            const modal = new bootstrap.Modal(document.getElementById('backupModal'));
            loadBackups(); // Load backups before showing modal
            modal.show();
        };
    }

    const createBackupButton = document.getElementById('createBackupButton');
    if (createBackupButton) {
        createBackupButton.addEventListener('click', createBackup);
    }

    // Initialize file upload handler
    const fileInput = document.getElementById('backupFileInput');
    if (fileInput) {
        fileInput.onchange = async function(e) {
            if (!e.target.files.length) return;
            
            const file = e.target.files[0];
            if (!file.name.endsWith('.json')) {
                showToast('error', 'Only JSON files are allowed');
                return;
            }
            
            try {
                showLoading('Uploading backup...');
                
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await fetch('/api/backup/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || 'Failed to upload backup');
                }
                
                const result = await response.json();
                showToast('success', 'Backup uploaded successfully');
                loadBackups(); // Refresh the backups list
                
                // Clear the file input
                e.target.value = '';
            } catch (error) {
                console.error('Error uploading backup:', error);
                showToast('error', error.message || 'Failed to upload backup');
            } finally {
                hideLoading();
            }
        };
    }
});

// Function to toggle section visibility
function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.toggle('expanded');
        
        // Find the icon in the header and rotate it
        const header = section.previousElementSibling;
        if (header) {
            const icon = header.querySelector('i.fas');
            if (icon) {
                icon.classList.toggle('fa-chevron-down');
                icon.classList.toggle('fa-chevron-right');
            }
        }
    }
}

// Function to toggle project details
function toggleProjectDetails(projectId) {
    const detailsDiv = document.getElementById(`project-details-${projectId}`);
    if (detailsDiv) {
        detailsDiv.classList.toggle('show');
        
        // Find the icon in the header and rotate it if it exists
        const projectDiv = detailsDiv.closest('.project-item');
        if (projectDiv) {
            const icon = projectDiv.querySelector('.item-header i.fas');
            if (icon) {
                icon.classList.toggle('fa-chevron-down');
                icon.classList.toggle('fa-chevron-right');
            }
        }
    }
}

// Function to toggle task details
function toggleTaskDetails(taskId) {
    const detailsDiv = document.getElementById(`task-details-${taskId}`);
    if (detailsDiv) {
        detailsDiv.classList.toggle('show');
        
        // Find the icon in the header and rotate it if it exists
        const taskDiv = detailsDiv.closest('.task-item');
        if (taskDiv) {
            const icon = taskDiv.querySelector('.item-header i.fas');
            if (icon) {
                icon.classList.toggle('fa-chevron-down');
                icon.classList.toggle('fa-chevron-right');
            }
        }
    }
}

// Calendar Initialization
function initializeCalendar() {
    const calendarEl = document.getElementById('calendar');
    calendar = new FullCalendar.Calendar(calendarEl, {
        timeZone: 'America/Denver',
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        editable: true,
        selectable: true,
        eventTimeFormat: {
            hour: 'numeric',
            minute: '2-digit',
            meridiem: 'short'
        },
        eventDidMount: function(info) {
            // Make task events more prominent
            if (info.event.extendedProps.type === 'task') {
                info.el.style.borderWidth = '2px';
                info.el.style.fontSize = '0.95em';
                info.el.style.fontWeight = '500';
            }
        },
        select: function(info) {
            // Debug log the raw times from FullCalendar
            console.log('Raw start:', info.start);
            console.log('Raw start hours:', info.start.getHours());
            console.log('Raw start timezone offset:', info.start.getTimezoneOffset());
            
            // Adjust for timezone offset (add 7 hours to correct the time)
            const start = moment(info.start).add(7, 'hours');
            const end = moment(info.end).add(7, 'hours');
            
            // Format for datetime-local input
            const startStr = start.format('YYYY-MM-DDTHH:mm');
            const endStr = end.format('YYYY-MM-DDTHH:mm');
            
            console.log('Adjusted start time:', startStr);
            console.log('Adjusted end time:', endStr);
            
            document.getElementById('eventStart').value = startStr;
            document.getElementById('eventEnd').value = endStr;
            
            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('addEventModal'));
            modal.show();
        },
        eventClick: function(info) {
            showEditEventModal(info.event);
        },
        eventDrop: function(info) {
            updateEventTime(info.event);
        },
        eventResize: function(info) {
            updateEventTime(info.event);
        },
        events: function(fetchInfo, successCallback, failureCallback) {
            fetch('/api/calendar')
                .then(response => response.json())
                .then(events => {
                    // Convert UTC ISO strings to local dates
                    const formattedEvents = events.map(event => ({
                        ...event,
                        start: moment.utc(event.start).local().format(),
                        end: moment.utc(event.end).local().format()
                    }));
                    successCallback(formattedEvents);
                })
                .catch(error => {
                    console.error('Error fetching events:', error);
                    failureCallback(error);
                });
        }
    });
    calendar.render();
}

// Task Management Functions
async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        if (!response.ok) {
            throw new Error(`Failed to fetch tasks: ${response.statusText}`);
        }
        const data = await response.json();
        
        const tasksList = document.getElementById('tasks-list');
        if (!tasksList) {
            console.error('Tasks list element not found');
            return;
        }
        
        tasksList.innerHTML = '';
        
        const tasks = Array.isArray(data) ? data : (data.tasks || []);
        
        if (tasks.length === 0) {
            tasksList.innerHTML = `
                <div class="alert alert-info">
                    No tasks found. Click the "Add Task" button to create your first task.
                </div>
            `;
            return;
        }
        
        tasks.forEach(async task => {
            const projectOptions = await getProjectOptionsHtml(task.project_id);
            const taskDependencyOptions = await getTaskOptionsHtml(task.id, task.dependencies);
            const taskElement = document.createElement('div');
            taskElement.className = 'task-item mb-3';
            taskElement.id = `task-${task.id}`;
            
            const projectColor = task.project ? task.project.color : '#6c757d';
            const statusClass = getStatusClass(task.status);
            
            // Apply a light version of the project color to the task background
            const rgbColor = hexToRgb(projectColor);
            const backgroundColor = rgbColor ? `rgba(${rgbColor.r}, ${rgbColor.g}, ${rgbColor.b}, 0.1)` : '#ffffff';
            taskElement.style.backgroundColor = backgroundColor;
            taskElement.style.borderLeft = `4px solid ${projectColor}`;
            
            taskElement.innerHTML = `
                <div class="item-header d-flex justify-content-between align-items-center p-2" style="cursor: pointer;" onclick="toggleTaskContent(${task.id})">
                    <div>
                        <span class="badge" style="background-color: ${projectColor}">&nbsp;</span>
                        <span class="task-title">${task.title}</span>
                        <span class="badge ${statusClass}">${task.status}</span>
                    </div>
                    <div>
                        <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteTask(${task.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="item-content p-3" id="task-content-${task.id}" style="display: none;">
                    <div class="form-group">
                        <label>Title</label>
                        <input type="text" class="form-control" value="${task.title}" 
                               onchange="updateTask(${task.id}, 'title', this.value)">
                    </div>
                    <div class="form-group mt-2">
                        <label>Status</label>
                        <select class="form-control" onchange="updateTask(${task.id}, 'status', this.value)">
                            ${getStatusOptionsHtml(task.status)}
                        </select>
                    </div>
                    <div class="form-group mt-2">
                        <label>Current Status Update</label>
                        <textarea class="form-control" rows="2" 
                            placeholder="Enter current status details..."
                            onchange="updateTask(${task.id}, 'current_status', this.value)">${task.current_status || ''}</textarea>
                    </div>
                    <div class="form-group mt-2">
                        <label>Priority</label>
                        <select class="form-control" onchange="updateTask(${task.id}, 'priority', this.value)">
                            ${getPriorityOptionsHtml(task.priority)}
                        </select>
                    </div>
                    <div class="form-group mt-2">
                        <label>Estimated Duration (minutes)</label>
                        <input type="number" class="form-control" value="${task.estimated_minutes || ''}" 
                               onchange="updateTask(${task.id}, 'estimated_minutes', this.value)">
                    </div>
                    <div class="form-group mt-2">
                        <label>Project</label>
                        <select class="form-control" onchange="updateTask(${task.id}, 'project_id', this.value)">
                            <option value="">No Project</option>
                            ${projectOptions}
                        </select>
                    </div>
                    <div class="form-group mt-2">
                        <label>Dependencies</label>
                        <select class="form-control" multiple onchange="updateTaskDependencies(${task.id}, Array.from(this.selectedOptions).map(opt => opt.value))">
                            ${taskDependencyOptions}
                        </select>
                    </div>
                </div>
            `;
            
            tasksList.appendChild(taskElement);
        });
    } catch (error) {
        console.error('Error loading tasks:', error);
        showToast('error', 'Failed to load tasks');
    }
}

function toggleTaskContent(taskId) {
    const content = document.getElementById(`task-content-${taskId}`);
    if (content) {
        const isHidden = content.style.display === 'none';
        content.style.display = isHidden ? 'block' : 'none';
        
        if (isHidden) {
            content.classList.add('fade-in');
        } else {
            content.classList.remove('fade-in');
        }
    }
}

async function updateTask(taskId, field = null, value = null) {
    try {
        let taskData;
        
        if (field && value !== null) {
            // Handle single field update
            if (field === 'title') {
                value = value.trim();
                if (!value) {
                    showToast('error', 'Title cannot be empty');
                    // Restore the original value in the input field
                    const input = document.querySelector(`#task-${taskId} input[type="text"]`);
                    if (input) {
                        const originalTitle = document.querySelector(`#task-${taskId} .item-header span:nth-child(2)`).textContent;
                        input.value = originalTitle;
                    }
                    return;
                }
            }
            
            taskData = {
                title: field === 'title' ? value : document.querySelector(`#task-${taskId} .item-header span:nth-child(2)`).textContent,
                [field]: field === 'project_id' || field === 'priority' || field === 'estimated_minutes' 
                    ? (value ? parseInt(value) : null)
                    : value.trim()
            };
        } else {
            // Handle full form update
            const title = document.getElementById('taskTitle').value.trim();
            if (!title) {
                showToast('error', 'Title cannot be empty');
                return;
            }
            
            taskData = {
                title: title,
                description: (document.getElementById('taskDescription').value || '').trim(),
                ticket_number: (document.getElementById('taskTicketNumber').value || '').trim(),
                project_id: parseInt(document.getElementById('taskProject').value) || null,
                priority: parseInt(document.getElementById('taskPriority').value) || null,
                estimated_minutes: parseInt(document.getElementById('taskDuration').value) || null,
                status: document.getElementById('taskStatus').value,
                dependencies: Array.from(document.getElementById('taskDependencies').selectedOptions)
                    .map(opt => parseInt(opt.value))
                    .filter(id => !isNaN(id))
            };
        }

        console.log('Updating task:', taskId, 'with data:', taskData); // Debug log

        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            console.error('Server error:', errorData); // Debug log
            throw new Error(errorData?.message || 'Failed to update task');
        }

        // Only hide modal if we're doing a full form update
        if (!field) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('addTaskModal'));
            if (modal) modal.hide();
        }

        // Reload tasks and show success message
        showToast('success', 'Task updated successfully');
        await loadTasks();
        
        // If this was a title update, update the displayed title without waiting for reload
        if (field === 'title' && value) {
            const titleSpan = document.querySelector(`#task-${taskId} .item-header span:nth-child(2)`);
            if (titleSpan) {
                titleSpan.textContent = value.trim();
            }
        }
    } catch (error) {
        console.error('Error updating task:', error);
        showToast('error', error.message || 'Failed to update task');
        
        // Restore the original value in the input field if this was a single field update
        if (field === 'title') {
            const input = document.querySelector(`#task-${taskId} input[type="text"]`);
            if (input) {
                const originalTitle = document.querySelector(`#task-${taskId} .item-header span:nth-child(2)`).textContent;
                input.value = originalTitle;
            }
        }
    }
}

// Task Modal Functions
function showAddTaskModal() {
    // Reset form
    document.getElementById('taskId').value = '';
    document.getElementById('taskTitle').value = '';
    document.getElementById('taskDescription').value = '';
    document.getElementById('taskTicketNumber').value = '';
    document.getElementById('taskDuration').value = '60';
    document.getElementById('taskStatus').value = 'Not Started';
    document.getElementById('taskPriority').value = '2';
    
    // Reset time tracking
    document.getElementById('taskTimeTracking').style.display = 'none';
    document.getElementById('taskStartedAt').textContent = '-';
    document.getElementById('taskCompletedAt').textContent = '-';
    document.getElementById('taskActualDuration').textContent = '-';
    
    // Load projects for dropdown
    loadProjectsForTaskModal();
    
    // Update modal title
    document.getElementById('taskModalTitle').textContent = 'Add Task';
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('addTaskModal'));
    modal.show();
}

async function addTask() {
    try {
        const taskData = {
            title: document.getElementById('taskTitle').value,
            description: document.getElementById('taskDescription').value,
            ticket_number: document.getElementById('taskTicketNumber').value,
            project_id: parseInt(document.getElementById('taskProject').value),
            priority: parseInt(document.getElementById('taskPriority').value),
            estimated_minutes: parseInt(document.getElementById('taskDuration').value),
            status: document.getElementById('taskStatus').value,
            dependencies: Array.from(document.getElementById('taskDependencies').selectedOptions).map(opt => parseInt(opt.value))
        };

        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        });

        if (!response.ok) {
            throw new Error('Failed to create task');
        }

        // Hide the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addTaskModal'));
        modal.hide();

        // Reload tasks
        showToast('success', 'Task created successfully');
        await loadTasks();
    } catch (error) {
        console.error('Error creating task:', error);
        showToast('error', 'Failed to create task');
    }
}

async function showEditTaskModal(task) {
    try {
        console.log('Showing edit modal for task:', task);
        
        // Set task ID
        const taskIdInput = document.getElementById('taskId');
        if (taskIdInput) {
            taskIdInput.value = task.id;
        }
        
        // Set basic task information
        const fields = {
            'taskTitle': task.title,
            'taskDescription': task.description || '',
            'taskTicketNumber': task.ticket_number || '',
            'taskPriority': task.priority,
            'taskStatus': task.status,
            'taskDuration': task.estimated_minutes || 60
        };
        
        for (const [id, value] of Object.entries(fields)) {
            const element = document.getElementById(id);
            if (element) {
                element.value = value;
            }
        }
        
        // Show delete button and update title for edit mode
        document.getElementById('deleteTaskBtn').style.display = 'block';
        document.getElementById('taskModalTitle').textContent = 'Edit Task';
        
        // Load projects and set the selected project
        await loadProjectsForTaskModal('taskProject', task.project_id);
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('addTaskModal'));
        modal.show();
    } catch (error) {
        console.error('Error showing edit task modal:', error);
        showToast('error', 'Failed to load task details');
    }
}

// Project Functions
async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        if (!response.ok) {
            throw new Error('Failed to load projects');
        }
        projects = await response.json();
        displayProjects();
        // After loading projects, load tasks since they depend on project data
        await loadTasks();
    } catch (error) {
        console.error('Error loading projects:', error);
        showToast('error', 'Failed to load projects');
    }
}

function displayProjects() {
    const projectsList = document.getElementById('projects-list');
    if (!projectsList) return;

    projectsList.innerHTML = '';
    if (projects.length === 0) {
        projectsList.innerHTML = '<div class="text-muted text-center">No projects available</div>';
        return;
    }

    projects.forEach(project => {
        const projectDiv = document.createElement('div');
        projectDiv.className = 'project-item mb-2';
        projectDiv.style.borderLeft = `4px solid ${project.color}`;
        projectDiv.style.backgroundColor = project.color + '10'; // 10% opacity

        projectDiv.innerHTML = `
            <div class="item-header" onclick="toggleProjectDetails(${project.id})">
                <div>
                    <span class="project-title">
                        <i class="fas fa-chevron-right me-1"></i>
                        ${project.name}
                    </span>
                    <span class="badge" style="background-color: ${project.color}; color: ${getContrastColor(project.color)}">
                        ${project.status}
                    </span>
                </div>
                <div>
                    <button class="btn btn-sm btn-link text-muted" onclick="event.stopPropagation(); editProject(${project.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                </div>
            </div>
            <div id="project-details-${project.id}" class="item-content">
                <p class="mb-2">${project.description || 'No description'}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">
                        Due: ${project.due_date ? new Date(project.due_date).toLocaleDateString() : 'No due date'}
                    </small>
                    <div>
                        <span class="badge bg-info">
                            ${project.priority || 'No priority'}
                        </span>
                    </div>
                </div>
            </div>
        `;
        
        projectsList.appendChild(projectDiv);
    });
}

async function editProject(projectId) {
    try {
        showLoading('Loading project...');
        
        // Fetch project details
        const response = await fetch(`/api/projects/${projectId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch project');
        }
        
        const project = await response.json();
        
        // Populate the modal
        const modal = new bootstrap.Modal(document.getElementById('addProjectModal'));
        document.getElementById('projectId').value = project.id;
        document.getElementById('projectName').value = project.name;
        document.getElementById('projectDescription').value = project.description || '';
        document.getElementById('projectDueDate').value = project.due_date ? project.due_date.split('T')[0] : '';
        document.getElementById('projectColor').value = project.color || '#6c757d';
        document.getElementById('projectStatus').value = project.status || 'active';
        document.getElementById('projectPriority').value = project.priority || 'medium';
        
        // Update modal title
        document.getElementById('projectModalTitle').textContent = 'Edit Project';
        
        // Show delete button
        const deleteBtn = document.getElementById('deleteProjectBtn');
        if (deleteBtn) {
            deleteBtn.style.display = 'block';
            deleteBtn.onclick = () => deleteProject(projectId);
        }
        
        modal.show();
    } catch (error) {
        console.error('Error loading project:', error);
        showToast('error', error.message || 'Failed to load project');
    } finally {
        hideLoading();
    }
}

async function deleteProject(projectId) {
    if (!confirm('Are you sure you want to delete this project? This will also delete all associated tasks.')) {
        return;
    }
    
    try {
        showLoading('Deleting project...');
        
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete project');
        }
        
        // Close modal if open
        const modal = bootstrap.Modal.getInstance(document.getElementById('addProjectModal'));
        if (modal) {
            modal.hide();
        }
        
        showToast('success', 'Project deleted successfully');
        loadProjects(); // Refresh the list
    } catch (error) {
        console.error('Error deleting project:', error);
        showToast('error', error.message || 'Failed to delete project');
    } finally {
        hideLoading();
    }
}

async function saveProject() {
    try {
        showLoading('Saving project...');
        
        // Get form values
        const projectId = document.getElementById('projectId').value;
        const name = document.getElementById('projectName').value;
        const description = document.getElementById('projectDescription').value;
        const dueDate = document.getElementById('projectDueDate').value;
        const color = document.getElementById('projectColor').value;
        const status = document.getElementById('projectStatus').value;
        const priority = document.getElementById('projectPriority').value;
        
        // Validate required fields
        if (!name) {
            throw new Error('Project name is required');
        }
        
        const projectData = {
            name,
            description,
            due_date: dueDate || null,
            color,
            status,
            priority
        };
        
        // Determine if this is an update or create
        const method = projectId ? 'PUT' : 'POST';
        const url = projectId ? `/api/projects/${projectId}` : '/api/projects';
        
        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(projectData)
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to save project');
        }
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addProjectModal'));
        if (modal) {
            modal.hide();
        }
        
        // Reset form
        document.getElementById('projectId').value = '';
        document.getElementById('projectName').value = '';
        document.getElementById('projectDescription').value = '';
        document.getElementById('projectDueDate').value = '';
        document.getElementById('projectColor').value = '#6c757d';
        document.getElementById('projectStatus').value = 'active';
        document.getElementById('projectPriority').value = 'medium';
        
        // Hide delete button
        const deleteBtn = document.getElementById('deleteProjectBtn');
        if (deleteBtn) {
            deleteBtn.style.display = 'none';
        }
        
        showToast('success', `Project ${projectId ? 'updated' : 'created'} successfully`);
        loadProjects(); // Refresh the list
    } catch (error) {
        console.error('Error saving project:', error);
        showToast('error', error.message || 'Failed to save project');
    } finally {
        hideLoading();
    }
}

function showAddProjectModal() {
    // Reset form
    document.getElementById('projectId').value = '';
    document.getElementById('projectName').value = '';
    document.getElementById('projectDescription').value = '';
    document.getElementById('projectDueDate').value = '';
    document.getElementById('projectColor').value = '#6c757d';
    document.getElementById('projectStatus').value = 'active';
    document.getElementById('projectPriority').value = 'medium';
    
    // Hide delete button
    const deleteBtn = document.getElementById('deleteProjectBtn');
    if (deleteBtn) {
        deleteBtn.style.display = 'none';
    }
    
    // Update modal title
    document.getElementById('projectModalTitle').textContent = 'Add Project';
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('addProjectModal'));
    modal.show();
}

// Event Management Functions
function formatDateTimeLocal(date) {
    // Ensure the date is treated as local time
    return moment(date).format('YYYY-MM-DDTHH:mm');
}

function showAddEventModal(start = null, end = null) {
    document.getElementById('eventModalTitle').textContent = 'Add Event';
    document.getElementById('eventId').value = '';
    document.getElementById('eventTitle').value = '';
    document.getElementById('eventDescription').value = '';
    document.getElementById('deleteEventBtn').style.display = 'none';
    
    if (start) {
        // Format the local time for the input
        document.getElementById('eventStart').value = formatDateTimeLocal(start);
    }
    if (end) {
        // Format the local time for the input
        document.getElementById('eventEnd').value = formatDateTimeLocal(end);
    }
    
    const modal = new bootstrap.Modal(document.getElementById('addEventModal'));
    modal.show();
}

function showEditEventModal(event) {
    console.log('Opening edit modal for event:', event);
    
    // Store the event ID globally
    currentEventId = event.id;
    console.log('Stored event ID:', currentEventId);
    
    const modal = document.getElementById('addEventModal');
    const title = document.getElementById('eventModalTitle');
    const deleteBtn = document.getElementById('deleteEventBtn');
    
    document.getElementById('eventId').value = event.id;
    document.getElementById('eventTitle').value = event.title;
    document.getElementById('eventStart').value = moment(event.start).format('YYYY-MM-DDTHH:mm');
    document.getElementById('eventEnd').value = moment(event.end).format('YYYY-MM-DDTHH:mm');
    document.getElementById('eventDescription').value = event.extendedProps.description || '';

    title.textContent = 'Edit Event';
    deleteBtn.style.display = 'block';
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // Clear event ID when modal is hidden
    modal.addEventListener('hidden.bs.modal', function () {
        currentEventId = null;
    }, { once: true });
}

async function saveEvent() {
    try {
        const titleElement = document.getElementById('eventTitle');
        const startElement = document.getElementById('eventStart');
        const endElement = document.getElementById('eventEnd');
        const descriptionElement = document.getElementById('eventDescription');
        
        // Validate form elements exist
        if (!titleElement || !startElement || !endElement) {
            throw new Error('Required form elements not found');
        }
        
        const title = titleElement.value;
        const start = startElement.value;
        const end = endElement.value;
        const description = descriptionElement ? descriptionElement.value : '';
        
        if (!title || !start || !end) {
            throw new Error('Please fill in all required fields');
        }
        
        // Format times in MST
        const startTime = moment(start).format('YYYY-MM-DDTHH:mm:ss');
        const endTime = moment(end).format('YYYY-MM-DDTHH:mm:ss');
        
        const eventData = {
            title: title,
            start_time: startTime,
            end_time: endTime,
            description: description,
            event_type: 'event'
        };
        
        const response = await fetch('/api/calendar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(eventData)
        });

        if (!response.ok) {
            throw new Error('Failed to save event');
        }

        const savedEvent = await response.json();
        
        // Add event to calendar with proper timezone
        calendar.addEvent({
            ...savedEvent,
            start: moment.tz(startTime, 'America/Denver').format(),
            end: moment.tz(endTime, 'America/Denver').format()
        });
        
        // Hide modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addEventModal'));
        if (modal) {
            modal.hide();
        }
        
        showToast('success', 'Event saved successfully');
    } catch (error) {
        console.error('Error saving event:', error);
        showToast('error', error.message || 'Failed to save event');
    }
}

async function updateEventTime(event) {
    try {
        const response = await fetch(`/api/calendar/${event.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: event.title,
                start_time: moment(event.start).utc().format(),
                end_time: moment(event.end).utc().format(),
                description: event.extendedProps.description || ''
            })
        });

        if (!response.ok) {
            throw new Error('Failed to update event');
        }

        showToast('Success', 'Event updated successfully', 'success');
    } catch (error) {
        console.error('Error updating event:', error);
        showToast('Error', error.message || 'Failed to update event', 'error');
        event.revert();
    }
}

async function deleteEvent(eventId) {
    try {
        console.log('Deleting event with ID:', eventId);
        
        if (!eventId) {
            throw new Error('No event selected for deletion');
        }

        const event = calendar.getEventById(eventId);
        console.log('Found event:', event);

        if (!event) {
            throw new Error('Event not found');
        }

        // Delete from backend first
        const response = await fetch(`/api/calendar/${eventId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to delete event');
        }

        // If backend deletion was successful, remove from calendar
        event.remove();
        
        // Close the modal
        const modal = document.getElementById('addEventModal');
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }
        
        showToast('success', 'Event deleted successfully');
    } catch (error) {
        console.error('Error deleting event:', error);
        showToast('error', error.message || 'Failed to delete event');
    }
}

// AI Analysis Functions
async function analyzeTasks() {
    try {
        showLoading('AI is analyzing your tasks...');
        console.log('Starting task analysis...');
        const response = await fetch('/api/tasks/analyze');
        console.log('Response received:', response);
        
        if (!response.ok) {
            throw new Error('Failed to analyze tasks');
        }

        const data = await response.json();
        console.log('Analysis data:', data);
        
        // Create and show modal for analysis results
        const modalHtml = `
            <div class="modal fade" id="analysisModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-brain text-primary"></i> 
                                Task Analysis Results
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="analysis-content">
                                ${data.analysis.split('\n').map(line => `<p>${line}</p>`).join('')}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if it exists
        const existingModal = document.getElementById('analysisModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add new modal to the document
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('analysisModal'));
        modal.show();

        showToast('success', 'Task analysis completed');
    } catch (error) {
        console.error('Error analyzing tasks:', error);
        showToast('error', 'Failed to analyze tasks');
    } finally {
        hideLoading();
    }
}

// Schedule Generation Functions
async function generateSchedule() {
    try {
        showLoading('Generating schedule suggestions...');
        console.log('Generating schedule suggestions...');
        
        // Get all calendar events
        const events = calendar.getEvents();
        console.log('All calendar events:', events);
        
        // Extract task IDs from calendar events
        const scheduledTaskIds = events
            .filter(event => event.extendedProps && event.extendedProps.task_id)
            .map(event => event.extendedProps.task_id);
        console.log('Already scheduled task IDs:', scheduledTaskIds);

        const response = await fetch('/api/schedule/suggestions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scheduled_task_ids: scheduledTaskIds
            })
        });

        if (!response.ok) {
            throw new Error('Failed to get schedule suggestions');
        }

        const suggestions = await response.json();
        console.log('Received suggestions:', suggestions);

        // Show the suggestions panel
        const aiSuggestions = document.getElementById('ai-suggestions');
        const aiContent = document.getElementById('ai-content');
        aiContent.innerHTML = '';  // Clear previous content

        if (suggestions.length === 0) {
            aiContent.innerHTML = '<p>No scheduling suggestions available at this time.</p>';
            aiSuggestions.style.display = 'block';
            return;
        }

        suggestions.forEach(suggestion => {
            const card = document.createElement('div');
            card.className = 'card mb-3';
            card.innerHTML = `
                <div class="card-body">
                    <h5 class="card-title">${suggestion.task_title}</h5>
                    <p class="card-text">
                        <i class="far fa-clock"></i> ${new Date(suggestion.suggested_time).toLocaleString()}
                    </p>
                    <p class="card-text">
                        <i class="fas fa-info-circle"></i> Task requires approximately ${suggestion.duration / 60} hours | 
                        Task is already in progress | Suggested start time:
                        ${new Date(suggestion.suggested_time).toLocaleTimeString()} on ${new Date(suggestion.suggested_time).toLocaleDateString()}
                    </p>
                    <button class="btn btn-success approve-btn" data-task-id="${suggestion.task_id}" 
                            data-time="${suggestion.suggested_time}" data-duration="${suggestion.duration}">
                        <i class="fas fa-check"></i> Approve
                    </button>
                </div>
            `;

            // Add click handler for the approve button
            const approveBtn = card.querySelector('.approve-btn');
            approveBtn.addEventListener('click', () => {
                approveSuggestion(
                    suggestion.task_id,
                    suggestion.suggested_time,
                    suggestion.duration
                );
            });

            aiContent.appendChild(card);
        });

        aiSuggestions.style.display = 'block';
    } catch (error) {
        console.error('Error generating schedule:', error);
        showToast('error', 'Failed to generate schedule suggestions');
    } finally {
        hideLoading();
    }
}

async function approveSuggestion(taskId, suggestedTime, duration) {
    try {
        console.log('Approving suggestion:', { taskId, suggestedTime, duration });
        
        // Create calendar event
        const startTime = moment(suggestedTime).format('YYYY-MM-DDTHH:mm:ss');
        const endTime = moment(suggestedTime).add(duration, 'minutes').format('YYYY-MM-DDTHH:mm:ss');
        
        // Get task details
        const response = await fetch(`/api/tasks/${taskId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch task details');
        }
        const task = await response.json();
        
        // Add event to calendar
        const calendarEvent = {
            title: task.title,
            start_time: startTime,
            end_time: endTime,
            extendedProps: {
                type: 'task',
                task_id: taskId,
                project_id: task.project_id,
                project_name: task.project_name
            }
        };
        
        // Save to backend
        const saveResponse = await fetch('/api/calendar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(calendarEvent)
        });

        if (!saveResponse.ok) {
            throw new Error('Failed to save calendar event');
        }

        const savedEvent = await saveResponse.json();
        
        // Add to calendar with proper timezone handling
        calendar.addEvent({
            ...savedEvent,
            start: moment.tz(startTime, 'America/Denver').format(),
            end: moment.tz(endTime, 'America/Denver').format(),
            extendedProps: {
                type: 'task',
                task_id: taskId,
                project_id: task.project_id,
                project_name: task.project_name
            }
        });
        
        // Hide the suggestion
        const suggestionElement = document.querySelector(`[data-task-id="${taskId}"]`).closest('.card');
        if (suggestionElement) {
            suggestionElement.remove();
        }
        
        // If no more suggestions, hide the panel
        const aiContent = document.getElementById('ai-content');
        if (!aiContent.children.length) {
            document.getElementById('ai-suggestions').style.display = 'none';
        }
        
        showToast('success', 'Task scheduled successfully');
    } catch (error) {
        console.error('Error approving suggestion:', error);
        showToast('error', 'Failed to schedule task');
    }
}

function closeAISuggestions() {
    const aiSuggestions = document.getElementById('ai-suggestions');
    aiSuggestions.classList.remove('show');
    setTimeout(() => {
        aiSuggestions.style.display = 'none';
    }, 300); // Match this with the CSS transition duration
}

// Utility Functions
function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    const toastContainer = document.getElementById('toastContainer');
    if (toastContainer) {
        toastContainer.appendChild(toast);
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 3000);
    } else {
        console.error('Toast container not found');
    }
}

function getTaskTitle(taskId) {
    const task = tasks.find(t => t.id === parseInt(taskId, 10));
    return task ? task.title : 'Unknown Task';
}

function getTaskColor(taskId) {
    const task = tasks.find(t => t.id === parseInt(taskId, 10));
    return task && task.project_color ? task.project_color : '#6c757d';  // Default to gray if no color found
}

function getStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'completed':
            return 'success';
        case 'in progress':
            return 'primary';
        case 'pending':
            return 'warning';
        default:
            return 'secondary';
    }
}

function getStatusBackground(status) {
    switch (status) {
        case 'Not Started': return '#f8f9fa';  // Light gray
        case 'In Progress': return '#e8f4ff';  // Light blue
        case 'Completed': return '#e8f8e8';  // Light green
        default: return '#ffffff';  // White
    }
}

function getPriorityClass(priority) {
    return {
        1: 'bg-danger',    // High priority
        2: 'bg-warning',   // Medium priority
        3: 'bg-info'       // Low priority
    }[priority] || 'bg-secondary';
}

async function generateStatusReport() {
    try {
        showLoading('Generating status report...');
        console.log('Generating status report...'); // Debug log
        
        const response = await fetch('/api/status-report');
        console.log('Response received:', response.status); // Debug log
        
        if (!response.ok) {
            throw new Error(`Failed to generate status report: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Data received:', data); // Debug log
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Convert markdown to HTML using marked
        const reportHtml = marked.parse(data.report);
        
        // Display the report in the modal
        const reportContent = document.getElementById('statusReportContent');
        reportContent.innerHTML = reportHtml;
        
        // Show the modal
        const modal = document.getElementById('statusReportModal');
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        showToast('success', 'Status report generated successfully');
    } catch (error) {
        console.error('Error generating status report:', error);
        showToast('error', error.message || 'Failed to generate status report');
    } finally {
        hideLoading();
    }
}

async function copyStatusReport() {
    try {
        const reportContent = document.getElementById('statusReportContent');
        const textContent = reportContent.innerText;
        await navigator.clipboard.writeText(textContent);
        showToast('Success', 'Report copied to clipboard', 'success');
    } catch (error) {
        console.error('Error copying report:', error);
        showToast('Error', 'Failed to copy report', 'error');
    }
}

// Project color generation
const projectColors = {};

// Base colors with high saturation and good contrast
const baseColors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD',
    '#D4A5A5', '#9A9EAB', '#A8E6CE', '#DCEDC2', '#FFD3B5'
];

// Generate a random color not in use
function generateUniqueColor() {
    // First try to use one of the base colors
    const unusedBaseColors = baseColors.filter(color => 
        !Object.values(projectColors).includes(color)
    );
    
    if (unusedBaseColors.length > 0) {
        return unusedBaseColors[Math.floor(Math.random() * unusedBaseColors.length)];
    }
    
    // If all base colors are used, generate a random color
    // that's sufficiently different from existing colors
    let newColor;
    let attempts = 0;
    const maxAttempts = 50;
    
    do {
        newColor = generateRandomColor();
        attempts++;
    } while (
        (isColorTooSimilarToExisting(newColor) || isColorTooDark(newColor)) && 
        attempts < maxAttempts
    );
    
    return newColor;
}

// Generate a random hex color
function generateRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

// Convert hex to RGB
function hexToRgb(hex) {
    // Remove the hash if present
    hex = hex.replace(/^#/, '');
    
    // Parse the hex values
    const bigint = parseInt(hex, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    
    return { r, g, b };
}

// Check if a color is too similar to existing colors
function isColorTooSimilarToExisting(newColor) {
    const existingColors = Object.values(projectColors);
    const newRgb = hexToRgb(newColor);
    
    return existingColors.some(existingColor => {
        const existingRgb = hexToRgb(existingColor);
        const distance = Math.sqrt(
            Math.pow(existingRgb.r - newRgb.r, 2) +
            Math.pow(existingRgb.g - newRgb.g, 2) +
            Math.pow(existingRgb.b - newRgb.b, 2)
        );
        return distance < 100; // Minimum distance threshold
    });
}

// Check if a color is too dark
function isColorTooDark(color) {
    const rgb = hexToRgb(color);
    const brightness = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
    
    return brightness < 128;
}

function getProjectColor(projectId) {
    if (!projectColors[projectId]) {
        projectColors[projectId] = generateUniqueColor();
    }
    return projectColors[projectId];
}

async function createBackup() {
    try {
        showLoading('Creating backup...');
        const response = await fetch('/api/backup', {
            method: 'POST',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to create backup');
        }

        const result = await response.json();
        showToast('success', 'Backup created successfully');
        loadBackups(); // Refresh the backups list
    } catch (error) {
        console.error('Error creating backup:', error);
        showToast('error', error.message || 'Failed to create backup');
    } finally {
        hideLoading();
    }
}

async function downloadBackup(filename) {
    try {
        showLoading('Preparing download...');
        const response = await fetch(`/api/backup/download/${filename}`);
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to download backup');
        }

        // Create a temporary link to trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showToast('success', 'Backup downloaded successfully');
    } catch (error) {
        console.error('Error downloading backup:', error);
        showToast('error', error.message || 'Failed to download backup');
    } finally {
        hideLoading();
    }
}

// Function to format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Function to load and display backups
async function loadBackups() {
    try {
        const response = await fetch('/api/backups');
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to load backups');
        }

        const backups = await response.json();
        const backupsList = document.getElementById('backups-list');
        if (!backupsList) {
            console.error('Backup list element not found');
            return;
        }

        backupsList.innerHTML = '';

        if (backups.length === 0) {
            backupsList.innerHTML = '<div class="list-group-item text-center text-muted">No backups available</div>';
            return;
        }

        backups.forEach(backup => {
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            
            const info = document.createElement('div');
            const createdAt = new Date(backup.created_at).toLocaleString();
            const size = formatFileSize(backup.size);
            
            info.innerHTML = `
                <h6 class="mb-0">${backup.filename}</h6>
                <small class="text-muted">
                    Created: ${createdAt}
                </small>
                <br>
                <small class="text-muted">
                    Size: ${size}
                </small>
            `;

            const actions = document.createElement('div');
            actions.className = 'btn-group';
            
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'btn btn-sm btn-outline-primary me-1';
            downloadBtn.innerHTML = '<i class="fas fa-download"></i>';
            downloadBtn.title = 'Download backup';
            downloadBtn.onclick = () => downloadBackup(backup.filename);
            
            const restoreBtn = document.createElement('button');
            restoreBtn.className = 'btn btn-sm btn-outline-warning me-1';
            restoreBtn.innerHTML = '<i class="fas fa-undo-alt"></i>';
            restoreBtn.title = 'Restore from backup';
            restoreBtn.onclick = () => restoreBackup(backup.filename);

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-sm btn-outline-danger';
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
            deleteBtn.title = 'Delete backup';
            deleteBtn.onclick = () => deleteBackup(backup.filename);

            actions.appendChild(downloadBtn);
            actions.appendChild(restoreBtn);
            actions.appendChild(deleteBtn);

            item.appendChild(info);
            item.appendChild(actions);
            backupsList.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading backups:', error);
        showToast('error', error.message || 'Failed to load backups');
    }
}

async function deleteBackup(filename) {
    if (!confirm(`Are you sure you want to delete backup: ${filename}?`)) {
        return;
    }

    try {
        showLoading('Deleting backup...');
        const response = await fetch(`/api/backup/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to delete backup');
        }

        showToast('success', 'Backup deleted successfully');
        loadBackups(); // Refresh the list
    } catch (error) {
        console.error('Error deleting backup:', error);
        showToast('error', error.message || 'Failed to delete backup');
    } finally {
        hideLoading();
    }
}

async function restoreBackup(filename) {
    if (!confirm('Are you sure you want to restore this backup? Current data will be replaced.')) {
        return;
    }
    
    try {
        showLoading('Restoring backup...');
        const response = await fetch(`/api/backup/restore?filename=${encodeURIComponent(filename)}`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to restore backup');
        }

        const result = await response.json();
        showToast('success', result.message || 'Backup restored successfully');
        setTimeout(() => window.location.reload(), 1000); // Reload after 1 second
    } catch (error) {
        console.error('Error restoring backup:', error);
        showToast('error', error.message || 'Failed to restore backup');
    } finally {
        hideLoading();
    }
}

// Add loading indicator functions
function showLoading(message = 'Processing...') {
    const loadingHtml = `
        <div id="loadingIndicator" class="position-fixed top-50 start-50 translate-middle bg-white p-4 rounded shadow-lg" style="z-index: 1060">
            <div class="d-flex align-items-center">
                <div class="spinner-border text-primary me-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div id="loadingMessage">${message}</div>
            </div>
        </div>
    `;
    
    // Remove existing loading indicator if any
    hideLoading();
    
    // Add new loading indicator
    document.body.insertAdjacentHTML('beforeend', loadingHtml);
}

function hideLoading() {
    const existing = document.getElementById('loadingIndicator');
    if (existing) {
        existing.remove();
    }
}

function getStatusClass(status) {
    switch (status) {
        case 'Not Started': return 'bg-secondary';
        case 'In Progress': return 'bg-primary';
        case 'Completed': return 'bg-success';
        default: return 'bg-secondary';
    }
}

async function getProjectOptionsHtml(selectedProjectId) {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        return projects.map(project => 
            `<option value="${project.id}" ${project.id === selectedProjectId ? 'selected' : ''}>
                ${project.name}
            </option>`
        ).join('');
    } catch (error) {
        console.error('Error getting project options:', error);
        return '';
    }
}

function getStatusOptionsHtml(selectedStatus) {
    const statuses = ['Not Started', 'In Progress', 'Completed'];
    return statuses.map(status => 
        `<option value="${status}" ${status === selectedStatus ? 'selected' : ''}>
            ${status}
        </option>`
    ).join('');
}

function getPriorityOptionsHtml(selectedPriority) {
    const priorities = [
        { value: 1, label: 'Low' },
        { value: 2, label: 'Medium' },
        { value: 3, label: 'High' }
    ];
    return priorities.map(priority => 
        `<option value="${priority.value}" ${priority.value === selectedPriority ? 'selected' : ''}>
            ${priority.label}
        </option>`
    ).join('');
}

async function getTaskOptionsHtml(currentTaskId, selectedTasks = []) {
    try {
        const response = await fetch('/api/tasks');
        if (!response.ok) {
            throw new Error(`Failed to fetch tasks: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Task options raw response:', data); // Debug log
        
        // Handle both possible response formats
        const tasks = data.tasks || data;
        if (!Array.isArray(tasks)) {
            console.error('Invalid tasks data structure:', data);
            throw new Error('Unexpected API response format');
        }

        // Filter out invalid tasks and the current task
        const validTasks = tasks.filter(task => 
            task && 
            typeof task === 'object' && 
            task.id !== currentTaskId && 
            task.title
        );

        if (validTasks.length === 0) {
            return '<option value="">No other tasks available</option>';
        }

        return validTasks
            .map(task => {
                const isSelected = Array.isArray(selectedTasks) && 
                    selectedTasks.some(dep => dep && dep.id === task.id);
                return `<option value="${task.id}" ${isSelected ? 'selected' : ''}>${task.title}</option>`;
            })
            .join('');
    } catch (error) {
        console.error('Error getting task options:', error);
        return '<option value="">Unable to load tasks</option>';
    }
}

function getRandomColor() {
    // List of pleasant, professional colors
    const colors = [
        '#4CAF50', // Green
        '#2196F3', // Blue
        '#9C27B0', // Purple
        '#FF9800', // Orange
        '#E91E63', // Pink
        '#00BCD4', // Cyan
        '#3F51B5', // Indigo
        '#FF5722', // Deep Orange
        '#009688', // Teal
        '#673AB7', // Deep Purple
        '#795548', // Brown
        '#607D8B'  // Blue Grey
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

async function createProject() {
    try {
        const projectName = document.getElementById('projectName').value;
        if (!projectName) {
            showToast('error', 'Please enter a project name');
            return;
        }

        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: projectName,
                color: getRandomColor()
            })
        });

        if (!response.ok) {
            throw new Error('Failed to create project');
        }

        // Hide modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('addProjectModal'));
        modal.hide();

        // Clear input
        document.getElementById('projectName').value = '';

        // Refresh projects list
        await loadProjects();
        showToast('success', 'Project created successfully');
    } catch (error) {
        console.error('Error creating project:', error);
        showToast('error', 'Failed to create project');
    }
}

// Function to get project color by ID
function getProjectColor(projectId) {
    const project = projects.find(p => p.id === projectId);
    return project ? project.color : '#6c757d'; // Default to gray if project not found
}

// Function to get contrasting text color
function getContrastColor(hexcolor) {
    // Remove the # if present
    hexcolor = hexcolor.replace('#', '');
    
    // Convert to RGB
    const r = parseInt(hexcolor.substr(0, 2), 16);
    const g = parseInt(hexcolor.substr(2, 2), 16);
    const b = parseInt(hexcolor.substr(4, 2), 16);
    
    // Calculate luminance
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    
    // Return black or white based on luminance
    return luminance > 0.5 ? '#000000' : '#ffffff';
}

// Update displayTasks to use project colors
function displayTasks() {
    const tasksList = document.getElementById('tasks-list');
    if (!tasksList) return;

    tasksList.innerHTML = '';
    if (tasks.length === 0) {
        tasksList.innerHTML = '<div class="text-muted text-center">No tasks available</div>';
        return;
    }

    tasks.forEach(task => {
        const taskDiv = document.createElement('div');
        taskDiv.className = 'task-item mb-2';
        
        // Get project color and set task background
        const projectColor = getProjectColor(task.project_id);
        const textColor = getContrastColor(projectColor);
        
        // Apply colors with reduced opacity for background
        taskDiv.style.backgroundColor = projectColor + '20'; // 20 = 12.5% opacity
        taskDiv.style.borderLeft = `4px solid ${projectColor}`;
        
        const project = projects.find(p => p.id === task.project_id);
        const projectName = project ? project.name : 'No Project';
        
        const statusBadgeColor = projectColor;
        const statusBadgeTextColor = getContrastColor(projectColor);

        taskDiv.innerHTML = `
            <div class="item-header d-flex justify-content-between align-items-center p-2" style="cursor: pointer;" onclick="toggleTaskDetails(${task.id})">
                <div>
                    <span class="badge" style="background-color: ${projectColor}">&nbsp;</span>
                    <span class="task-title">${task.title}</span>
                    <span class="badge ${getStatusClass(task.status)}">${task.status}</span>
                </div>
                <div>
                    <button class="btn btn-sm btn-link text-muted" onclick="event.stopPropagation(); editTask(${task.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                </div>
            </div>
            <div id="task-details-${task.id}" class="item-content">
                <p class="mb-2">${task.description || 'No description'}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">
                        Due: ${task.due_date ? new Date(task.due_date).toLocaleDateString() : 'No due date'}
                    </small>
                    <span class="badge bg-${task.status === 'completed' ? 'success' : 'warning'}">
                        ${task.status}
                    </span>
                </div>
            </div>
        `;
        
        tasksList.appendChild(taskDiv);
    });
}

// Function to load projects for task modal
async function loadProjectsForTaskModal(selectId = 'taskProject', selectedProjectId = null) {
    try {
        showLoading('Loading projects...');
        
        const response = await fetch('/api/projects');
        if (!response.ok) {
            throw new Error('Failed to load projects');
        }
        
        const projects = await response.json();
        const select = document.getElementById(selectId);
        
        if (!select) {
            console.error(`Project select element with id ${selectId} not found`);
            return;
        }
        
        // Clear existing options
        select.innerHTML = '';
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '-- Select Project --';
        select.appendChild(defaultOption);
        
        // Add project options
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = project.name;
            if (project.color) {
                option.style.backgroundColor = project.color;
                option.style.color = getContrastColor(project.color);
            }
            select.appendChild(option);
        });
        
        // Set selected project if provided
        if (selectedProjectId) {
            select.value = selectedProjectId;
        }
    } catch (error) {
        console.error('Error loading projects for task modal:', error);
        showToast('error', error.message || 'Failed to load projects');
    } finally {
        hideLoading();
    }
}

// Function to show add task modal
function showAddTaskModal() {
    // Reset form
    document.getElementById('taskId').value = '';
    document.getElementById('taskTitle').value = '';
    document.getElementById('taskDescription').value = '';
    document.getElementById('taskDueDate').value = '';
    document.getElementById('taskProject').value = '';
    document.getElementById('taskStatus').value = 'pending';
    document.getElementById('taskPriority').value = 'medium';
    
    // Reset time tracking
    document.getElementById('taskTimeTracking').style.display = 'none';
    document.getElementById('taskStartedAt').textContent = '-';
    document.getElementById('taskCompletedAt').textContent = '-';
    document.getElementById('taskActualDuration').textContent = '-';
    
    // Load projects for dropdown
    loadProjectsForTaskModal();
    
    // Update modal title
    document.getElementById('taskModalTitle').textContent = 'Add Task';
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('addTaskModal'));
    modal.show();
}