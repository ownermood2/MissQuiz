#!/bin/bash

# Telegram Quiz Bot - GitHub Push Script
# Run this script in the Shell to push your code

echo "🚀 Pushing code to GitHub..."
echo ""

# Configure git remote
git remote add origin https://github.com/ownermood2/MissQuiz.git 2>/dev/null || git remote set-url origin https://github.com/ownermood2/MissQuiz.git

# Add all changes
echo "📦 Adding all changes..."
git add .

# Commit
echo "💾 Committing changes..."
git commit -m "v2.2: Enhanced developer list format & broadcast persistence fixes"

# Push to GitHub
echo "📤 Pushing to GitHub..."
echo "Note: You will be asked for your GitHub username and token"
echo ""
git push -u origin main

echo ""
echo "✅ Done! Your code is now on GitHub."
echo "🔒 Remember to revoke any tokens you shared in chat!"
