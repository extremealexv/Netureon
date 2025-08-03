#!/bin/bash

echo "🚀 Setting up NetGuard environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔑 Creating .env file..."
    cat > .env << EOL
DB_NAME=netguard
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
EOL
    echo "⚠️ Please update the database credentials in .env file"
else
    echo "✅ .env file already exists"
fi

echo "✨ Setup complete! You can now run NetGuard using 'python main.py'"
