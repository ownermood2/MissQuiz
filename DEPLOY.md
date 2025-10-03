# 🚀 Deployment Guide - Telegram Quiz Bot

## ✅ Pre-Deployment Checklist

Before pushing to GitHub and deploying to Render, ensure:
- [x] All code is tested and working locally
- [x] Environment variables are documented
- [x] Deployment configs are correct (Procfile, render.yaml)
- [x] No hardcoded secrets in code
- [x] Database schema is stable

---

## 📋 Required Environment Variables

### For Render Deployment

Set these in your Render dashboard under **Environment** tab:

| Variable | Value | How to Get |
|----------|-------|------------|
| `TELEGRAM_TOKEN` | Your bot token | Get from [@BotFather](https://t.me/BotFather) - Send `/newbot` or `/token` |
| `SESSION_SECRET` | Random 64-char hex string | Run: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `OWNER_ID` | Your Telegram user ID | Get from [@userinfobot](https://t.me/userinfobot) - Send `/start` |
| `MODE` | `webhook` | Fixed value for Render deployment |
| `WEBHOOK_URL` | `https://YOUR-APP.onrender.com/webhook` | Replace YOUR-APP with your actual Render app name |
| `WIFU_ID` | (Optional) Additional admin ID | Get from [@userinfobot](https://t.me/userinfobot) if needed |

### Example SESSION_SECRET Generation

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Output example: 7a788000395b1cda60a6d14ec41b4cdacff286137f4c0d66f7708b0a7d84c32c
```

---

## 🌐 Render Deployment Steps

### Step 1: Push Code to GitHub

```bash
git add .
git commit -m "Ready for production deployment"
git push origin main
```

### Step 2: Create Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New"** → **"Web Service"**
3. Connect your GitHub repository
4. Render will auto-detect Python and use `render.yaml`

### Step 3: Configure Environment Variables

In Render dashboard → Your service → **Environment** tab:

1. Add all variables from the table above
2. **IMPORTANT**: Don't forget to set `WEBHOOK_URL` with your actual Render URL
3. Save changes

### Step 4: Deploy

1. Click **"Manual Deploy"** → **"Deploy latest commit"**
2. Wait 2-3 minutes for deployment
3. Check logs for errors

### Step 5: Verify Deployment

Test the health endpoint:
```bash
curl https://YOUR-APP.onrender.com/
# Expected output: {"status":"ok"}
```

Test the admin panel:
```bash
# Open in browser:
https://YOUR-APP.onrender.com/admin
```

---

## 🔧 Platform-Specific Deployment

### Replit (Polling Mode - Current)
Already configured! Just click **Run** button.
- Uses polling mode automatically
- No webhook needed
- Runs on port 5000

### Heroku
```bash
# Login and create app
heroku login
heroku create your-app-name

# Set environment variables
heroku config:set TELEGRAM_TOKEN=your_token
heroku config:set SESSION_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
heroku config:set OWNER_ID=your_id
heroku config:set MODE=webhook
heroku config:set WEBHOOK_URL=https://your-app-name.herokuapp.com/webhook

# Deploy
git push heroku main
```

### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and init
railway login
railway init

# Set environment variables in Railway dashboard
# Then deploy
railway up
```

### VPS / DigitalOcean (Polling Mode)
```bash
# Clone repository
git clone your-repo-url
cd telegram-quiz-bot

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_TOKEN=your_token
export SESSION_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
export OWNER_ID=your_id
export MODE=polling

# Run with systemd or screen
python main.py
```

---

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'app'"
**Solution**: Render is deploying old code. Push latest changes to GitHub and redeploy.

### Issue: "SESSION_SECRET environment variable is required"
**Solution**: Set `SESSION_SECRET` in Render environment variables.

### Issue: "Bot not responding to commands"
**Solution**: 
1. Check WEBHOOK_URL is correct (must end with `/webhook`)
2. Verify TELEGRAM_TOKEN is valid
3. Check Render logs for errors

### Issue: "Health check failing"
**Solution**: 
1. Ensure bot is starting without errors
2. Check `/` endpoint returns `{"status":"ok"}`
3. Verify port binding (should be `0.0.0.0:$PORT`)

### Issue: "Database not persisting"
**Solution**: 
1. Render free tier may reset disk storage
2. Consider upgrading to paid plan for persistent disk
3. Or use external PostgreSQL database

---

## 📊 Monitoring

### Check Bot Status on Render

1. **Logs**: Dashboard → Your service → **Logs** tab
2. **Health**: Check health endpoint every 5 minutes
3. **Metrics**: Monitor memory usage and response times

### Expected Startup Logs

```
INFO:src.core.database:Database initialized at data/quiz_bot.db
INFO:src.core.quiz:Successfully loaded and cleaned 229 questions
INFO:src.web.app:Quiz Manager initialized successfully
INFO:src.web.app:Telegram bot initialized successfully in webhook mode
INFO:werkzeug:Running on http://0.0.0.0:10000
```

---

## ✅ Deployment Complete Checklist

- [ ] Code pushed to GitHub
- [ ] Render service created and connected to repo
- [ ] All environment variables set correctly
- [ ] WEBHOOK_URL matches actual Render URL
- [ ] Deployment successful (no errors in logs)
- [ ] Health endpoint returns `{"status":"ok"}`
- [ ] Bot responds to `/start` command in Telegram
- [ ] Admin panel accessible at `/admin`
- [ ] Automated quizzes sending every 30 minutes

---

## 🎯 Quick Reference

**Render Start Command:**
```bash
MODE=webhook gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 main:app
```

**Health Check Endpoint:** `/`

**Admin Panel:** `/admin`

**Webhook Endpoint:** `/webhook`

**Expected Response Time:** < 3 seconds

---

## 📞 Support

If you encounter issues:
1. Check Render logs for error messages
2. Verify all environment variables are set
3. Test health endpoint with curl
4. Check Telegram bot token is valid
5. Ensure webhook URL is correct

**Bot Features:**
- ✅ 12 quiz categories
- ✅ Automated quizzes every 30 minutes
- ✅ Real-time statistics tracking
- ✅ Group chat management
- ✅ Admin panel for question management
- ✅ Graceful error recovery
- ✅ Network resilience
- ✅ Single-instance enforcement
