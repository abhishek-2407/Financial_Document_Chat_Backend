# Financial Document Chat Backend

This backend service powers a financial document analysis system. It includes user authentication, document management, summary generation, and more.

## ⚙️ Features

- User registration & login (JWT-based)
- Role-based access (`user`, `admin`, `master_admin`)
- Document upload & storage (S3)
- Summary file tracking
- Soft deletion of files
- Email invitations
- Token validation

---

## 🖥️ Requirements

- Python 3.9+
- Virtual environment support (`venv`)
- PostgreSQL database
- S3 bucket access for file storage

---

## 🔧 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/financial-doc-chat-backend.git
cd financial-doc-chat-backend
```

### 2. Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. System Dependencies (Required for WeasyPrint)
## Amazon Linux
```bash
sudo dnf install cairo cairo-devel pango pango-devel gdk-pixbuf2 gdk-pixbuf2-devel libffi libffi-devel redhat-rpm-config gcc python3-devel
```
## MacOs
```bash
brew install cairo pango gdk-pixbuf libffi
```

### 4 . ▶️ Run the App
```bash 
python3 main.py
```