# 🕵️ Instagram Follower Detective 🔍

*I definitely built this because I wanted to learn about async programming, web scraping, and distributed task queues and not because I care deeply about who unfollowed me on Instagram.* 😏

## 📸 Dashboard Preview
<div align="center">
  <img src="https://i.imgur.com/EE4sbMs.jpeg" alt="Instagram Follower Detective Dashboard" width="90%" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
</div>

---

## 🚀 Features

### 📊 **Real-time Follower Analytics**
- **Unfollower Detection**: Discover who had the audacity to unfollow you
- **Non-reciprocal Following**: Find users who don't follow you back (the nerve!)
- **Historical Snapshots**: Track changes over time with persistence
- **Beautiful Dashboard**: Modern, Instagram-inspired UI that's actually pleasant to look at

### 🔄 **Concurrent Processing**
- **Blazing Fast Scraping**: Simultaneous follower/following data collection
- **Rate Limit Handling**: Smart retry logic to avoid Instagram's watchful eye
- **Background Tasks**: Long-running operations don't block the UI
- **Progress Tracking**: Real-time status updates during scanning

### 🛡️ **Robust & Reliable**
- **Session Management**: Maintains authentic browser context
- **Cookie Persistence**: Remembers login sessions between runs
- **Error Handling**: Graceful degradation when things go sideways
- **Docker Ready**: Containerized for consistent deployment

---

## 🏗️ Technology Stack

### **🎭 Selenium WebDriver**
Controls a real Chrome browser to:
- Navigate Instagram's interface naturally
- Handle JavaScript-heavy pages
- Maintain authentic user sessions
- Extract authentication tokens and cookies

### **⚡ Async/Await with aiohttp**
Python concurrency for efficient data collection:
- **Coroutines**: Fetch followers and following lists simultaneously
- **Non-blocking I/O**: Efficient network operations
- **Connection Pooling**: Reuse HTTP connections for better performance
- **Timeout Management**: Prevent hanging requests

### **🔧 Celery Task Queue**
Distributed task processing:
- **Background Jobs**: Heavy scraping operations run asynchronously
- **Redis Backend**: Fast message broker for task coordination
- **Task Locking**: Prevents duplicate scans from running
- **Progress Tracking**: Real-time status updates

### **🐘 PostgreSQL Database**
Reliable data persistence:
- **Relational Design**: Proper foreign key relationships
- **Snapshot History**: Track changes over time
- **Efficient Queries**: Optimized for follower comparisons
- **ACID Compliance**: Data integrity guaranteed

### **🌐 Django Web Framework**
Full-featured web development:
- **MVT Architecture**: Clean separation of concerns
- **Template Engine**: Dynamic HTML generation
- **ORM**: Object-relational mapping for database operations
- **Admin Interface**: Built-in data management

### **🐳 Docker Containerization**
Development and deployment:
- **Multi-service Setup**: App, database, Redis, and worker containers
- **Environment Isolation**: Consistent runtime across systems
- **Volume Mounting**: Live code reloading during development
- **Health Checks**: Ensure services are ready before startup

---

## 🚦 Getting Started

### Prerequisites
- Docker & Docker Compose
- Git
- A sense of humor about social media metrics

### 1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/instagram-unfollow-automation.git
cd instagram-unfollow-automation
```

### 2. **Environment Configuration**
Create a `.env` file with the following variables:

```env
# Database Configuration
POSTGRES_DB=instagram_analyzer
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_secure_password

# Django Settings
SECRET_KEY=your-super-secret-django-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Instagram Credentials
INSTA_USER=your_instagram_username
INSTA_PASSWORD=your_instagram_password
```

### 3. **Launch the Application**
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f app
```

### 4. **Access the Dashboard**
Open your browser and navigate to: `http://localhost:8000/instagram/dashboard/`

### 5. **Run Your First Scan**
Click the "Start New Scan" button and watch the magic happen! ✨

---

## 🎯 How It Works

### **Phase 1: Authentication**
The system first attempts to log in using saved cookies. If that fails, it performs a fresh login and saves the new session for future use.

### **Phase 2: Session Extraction**
Using browser automation, the app extracts Instagram's internal API tokens and session data while maintaining the appearance of normal browsing behavior.

### **Phase 3: Concurrent Data Collection**
Two async tasks run simultaneously:
- **Followers Scraper**: Fetches your complete followers list
- **Following Scraper**: Fetches your complete following list

### **Phase 4: Data Analysis**
The system compares current data with the most recent snapshot to identify:
- Users who recently unfollowed you
- Users you follow who don't follow back

### **Phase 5: Visualization**
Beautiful, responsive dashboard displays insights with:
- Real-time progress indicators
- Interactive user lists
- Historical trend data

---

## 🔧 Architecture Highlights

### **Hybrid Scraping Approach**
Combines browser automation with direct API calls:
- Browser maintains authentic session state
- API calls handle bulk data collection
- Smart retry logic handles rate limiting

### **Distributed Processing**
Celery workers handle resource-intensive tasks:
- Main app stays responsive
- Multiple scans can be queued
- Background processing scales independently

### **Modern Frontend**
Instagram-inspired design with:
- Responsive grid layouts
- CSS animations and transitions
- Progressive loading states
- Mobile-optimized interface

---

## 📝 Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_DB` | Database name | `instagram_analyzer` |
| `POSTGRES_USER` | Database username | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `securepassword123` |
| `SECRET_KEY` | Django secret key | `your-50-char-secret-key` |
| `DJANGO_DEBUG` | Debug mode | `True` / `False` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hostnames | `localhost,127.0.0.1` |
| `INSTA_USER` | Instagram username | `your_username` |
| `INSTA_PASSWORD` | Instagram password | `your_password` |


---

## 🤝 Contributing

Found a bug? Want to add a feature? Think my code is terrible? Pull requests welcome! 

Just remember: this project exists purely for educational purposes and definitely not because I have trust issues with social media relationships. 😅

---

## ⚖️ Legal Notice

This tool is for educational purposes only. Use responsibly and in accordance with Instagram's Terms of Service. The author is not responsible for any account restrictions that may result from usage.

*Translation: Don't blame me if Instagram gets mad at you for being too curious about your follower count.*

---

## 🏆 Acknowledgments

- **Instagram**: For creating an addictive platform that makes us care about meaningless metrics
- **The Python Community**: For making async programming almost enjoyable
- **My Followers**: For the inspiration (and occasional betrayal) that led to this project
- **Coffee**: The real MVP behind this codebase

