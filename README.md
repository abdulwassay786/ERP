# Django ERP System

A small-scale internal ERP system built with Django, PostgreSQL, and HTMX.

## Features

- **Multi-Company Support**: Complete data isolation between companies
- **Customer Management**: Track customer information and relationships
- **Inventory Management**: Manage products with SKU, pricing, and stock levels
- **Invoice Management**: Create invoices with line items and status tracking
- **Banking Module**: Manual bank transaction tracking with file uploads
- **Soft Deletes**: Records are soft-deleted for audit purposes
- **HTMX Integration**: Dynamic UI with modal forms and inline updates

## Prerequisites

- Python 3.8+
- Virtual environment (venv)

## Setup Instructions

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install requirements (already done if you cloned the repo)
pip install -r requirements.txt
```

### 2. Run Migrations

```bash
python manage.py migrate
```

### 3. Create Superuser

```bash
python manage.py createsuperuser
```

### 4. Create a Company

After creating a superuser, you need to create a company and assign it to your user.

**Option 1: Using the helper script**

```bash
python create_company.py
```

**Option 2: Using Django shell**

```bash
python manage.py shell
```

Then in the shell:

```python
from apps.core.models import Company, User

# Create a company
company = Company.objects.create(
    name="My Company",
    address="123 Main St",
    tax_id="TAX123",
    phone="555-1234",
    email="info@mycompany.com"
)

# Assign company to superuser
user = User.objects.get(username='your_username')
user.company = company
user.save()

exit()
```

### 5. Run Development Server

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000 and login with your superuser credentials.

## Project Structure

```
ERP/
├── apps/
│   ├── core/          # Custom user, company, base models
│   ├── customers/     # Customer management
│   ├── inventory/     # Inventory management
│   ├── invoices/      # Invoice management
│   └── banking/       # Bank account tracking
├── templates/         # Django templates
├── static/           # CSS, JavaScript, images
├── media/            # Uploaded files
└── erp_project/      # Project settings
```

## Usage

### Multi-Company Setup

1. Login to Django admin (/admin/)
2. Create multiple companies
3. Create users and assign them to companies
4. Each user will only see data from their assigned company

### Module Features

**Customers**: Add, edit, delete customers with contact information

**Inventory**: Manage products with SKU, pricing, and stock tracking

**Invoices**: Create invoices with multiple line items, track status (draft, sent, paid, cancelled)

**Banking**: Track bank accounts and manual transactions with optional file uploads

## Technology Stack

- **Backend**: Django 4.2
- **Database**: SQLite (can be changed to PostgreSQL for production)
- **Frontend**: Django Templates + HTMX
- **Styling**: Custom CSS

## Security Notes

- Change the SECRET_KEY in settings.py for production
- Update database credentials in settings.py
- Set DEBUG = False in production
- Configure ALLOWED_HOSTS for production
