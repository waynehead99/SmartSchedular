# Smart Scheduler (Beta)

An AI-powered task and project management system that intelligently schedules tasks based on priorities and workload.

## Features

- **Project Management**
  - Create and manage projects with priorities (High, Medium, Low)
  - Assign custom colors to projects for visual organization
  - Track project status and progress

- **Task Management**
  - Create tasks with estimated durations
  - Set task priorities independent of project priorities
  - Associate tasks with specific projects

- **AI-Powered Scheduling**
  - Intelligent task scheduling based on combined project and task priorities
  - Respects working hours (9 AM - 5 PM)
  - Avoids weekend scheduling
  - Maintains buffer time between tasks
  - Considers existing calendar events to avoid conflicts

- **Calendar Integration**
  - Visual calendar interface using FullCalendar
  - Color-coded events based on project
  - Easy drag-and-drop scheduling

## Requirements

- Python 3.8+
- Flask
- SQLAlchemy
- OpenAI API key (for AI scheduling features)
- Modern web browser

## Installation

1. Clone the repository:
```bash
git clone https://github.com/waynehead99/smart_scheduler.git
cd smart_scheduler
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key and other configurations
```

5. Initialize the database:
```bash
python reset_db.py
```

## Docker Deployment

1. Clone the repository:
```bash
git clone https://github.com/waynehead99/SmartSchedular.git
cd SmartSchedular
```

2. Set up environment variables:
```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your settings
# Make sure to set your OpenAI API key and other required variables
nano .env  # or use your preferred text editor
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `FLASK_APP`: Set to `app.py`
- `FLASK_ENV`: Set to `production` for deployment
- `SECRET_KEY`: Your secret key for Flask sessions
- `SQLALCHEMY_DATABASE_URI`: SQLite database path (default: `sqlite:///instance/scheduler.db`)

3. Build and run with Docker:
```bash
# Build the Docker image
docker build -t smart-scheduler .

# Run the container
docker run -d -p 5000:5000 --env-file .env smart-scheduler

# Initialize the database (replace <container_id> with your container ID)
docker ps  # get the container ID
docker exec <container_id> python reset_db.py
```

4. Access the application:
- Open your browser and navigate to `http://<your-server-ip>:5000`
- The API endpoints will be available at `http://<your-server-ip>:5000/api/*`

## Usage

1. Start the server:
```bash
python app.py
```

2. Access the application at `http://localhost:5000`

3. Create projects and tasks:
   - Set priorities for both projects and tasks
   - Estimate task durations
   - Use the AI scheduling feature to get optimal scheduling suggestions

## API Endpoints

- `GET /api/projects` - List all projects
- `POST /api/projects` - Create a new project
- `GET /api/tasks` - List all tasks
- `POST /api/tasks` - Create a new task
- `GET /api/schedule/suggest` - Get AI-powered scheduling suggestions
- `GET /api/calendar` - Get calendar events

## Beta Notes

This is a beta release with the following limitations:

1. Calendar events are stored locally
2. No user authentication system yet
3. Limited to single user/organization
4. Basic AI scheduling algorithm

## Coming Soon

- Multi-user support with authentication
- Advanced AI scheduling with learning capabilities
- External calendar integration (Google Calendar, Outlook)
- Mobile application
- Task dependencies and subtasks
- Resource allocation and team management

## Contributing

This is a beta version, and we welcome contributions! Please submit issues and pull requests.

## License

MIT License - See LICENSE file for details
