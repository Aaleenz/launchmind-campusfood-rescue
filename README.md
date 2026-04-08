# launchmind-campusfood-rescue

## Multi-Agent System for Real-time Food Waste Alerts

![Status](https://img.shields.io/badge/status-working-brightgreen)
![Agents](https://img.shields.io/badge/agents-4-blue)
![Python](https://img.shields.io/badge/python-3.8+-blue)



## 📋 Startup Idea

**CampusFood Rescue** - A real-time notification system for leftover campus cafeteria food that would otherwise be thrown away.

### Value Proposition:
- Students get SMS alerts when food is available at discounted prices (30-50% off)
- Cafeteria managers get analytics on waste reduction
- Reduce campus food waste by 40% within 6 months
- Save average student Rs. 2,000 per semester

### Target Users:
- Hungry students looking for affordable meals
- Cafeteria managers wanting to reduce waste and increase revenue
- Campus sustainability departments tracking environmental impact

---

## 🏗️ Agent Architecture

```
                    ┌─────────────────┐
                    │   CEO AGENT     │
                    │  (Orchestrator) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  PRODUCT AGENT  │
                    │ (Spec Generator)│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
       │  ENGINEER   │ │ MARKETING  │ │    QA      │
       │   AGENT     │ │   AGENT    │ │  (Bonus)   │
       │  (GitHub)   │ │(Email/Slack)│ │(Reviewer)  │
       └─────────────┘ └────────────┘ └────────────┘
```

### Agent Roles & Responsibilities

| Agent | Role | Actions | Platform |
|-------|------|---------|----------|
| **CEO** | Orchestrator | Decomposes ideas, reviews outputs, manages feedback loops | Groq LLM |
| **Product** | Product Manager | Generates specs with personas, features, user stories | Groq LLM |
| **Engineer** | Developer | Creates HTML landing page, opens PRs, commits code | GitHub API |
| **Marketing** | Growth Marketer | Sends emails, posts to Slack, creates social content | SendGrid, Slack API |

---

## 🔄 Dynamic Feedback Loop

The system features a **real feedback loop** where the CEO agent:

1. Reviews each agent's output using LLM reasoning
2. Assigns a score (0-10) with specific feedback
3. Sends revision requests when quality is below 8/10
4. Tracks improvement across multiple revision attempts
5. Only approves when quality standards are met

### Results from Execution:

| Attempt | Score | Status |
|---------|-------|--------|
| Attempt 1 | 6/10 | REJECTED - Needs technical details |
| Attempt 2 | 6/10 | REJECTED - No improvement |
| Attempt 3 | 7/10 | APPROVED WITH WARNINGS |

**✅ Score improved from 6 → 7 across revisions**

---

## 📦 Platform Integrations

### 1. GitHub API
- Creates pull requests automatically
- Commits HTML landing pages
- Creates issues for tracking

### 2. Slack API (Block Kit)
- Posts to #launches channel
- Uses proper Block Kit formatting (header, sections, dividers, context)
- Rich formatting with mrkdwn text
- Bot authentication

### 3. SendGrid API
- Sends cold outreach emails
- 100 emails/day on free tier
- HTML formatted emails
- Verified sender authentication

### 4. Groq API
- LLM provider for all agents
- Llama 3.1 8B model
- Fast inference (< 2 seconds)
- Handles rate limits with retry logic



## 🛠️ Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Git
- GitHub account
- Slack workspace (free)
- SendGrid account (free tier)
- Groq API key (free)

### Step 1: Clone Repository

```bash
git clone https://github.com/Aaleenz/launchmind-campusfood-rescue.git
cd launchmind-campusfood-rescue
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables

Copy the example file and add your API keys:

bash
cp .env.example .env

Edit `.env` with your actual keys:

env
# Groq API (LLM Provider)
GROQ_API_KEY=gsk_your_groq_api_key_here

# GitHub Integration
GITHUB_TOKEN=github_pat_your_token_here
GITHUB_REPO=Aaleenz/launchmind-campusfood-rescue

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your_slack_bot_token_here

# SendGrid Email
SENDGRID_API_KEY=SG.your_sendgrid_key_here
VERIFIED_SENDER_EMAIL=your_verified_email@example.com
TEST_RECIPIENT_EMAIL=test@example.com


### Step 5: Platform Setup Details

#### GitHub Setup
1. Create public repo: `launchmind-campusfood-rescue`
2. Generate Personal Access Token with `repo` scope
3. Add token to `.env` as `GITHUB_TOKEN`

#### Slack Setup
1. Create workspace at https://slack.com
2. Create app at https://api.slack.com/apps
3. Add Bot Token Scopes: `chat:write`, `channels:read`, `channels:join`
4. Install to workspace and copy `xoxb-` token
5. Create `#launches` channel and invite bot: `/invite @YourBotName`

#### SendGrid Setup
1. Sign up at https://sendgrid.com (free tier)
2. Create API Key with "Mail Send" permission
3. Verify single sender email address
4. Add API key to `.env`

#### Groq Setup
1. Sign up at https://console.groq.com
2. Create API key
3. Add to `.env` as `GROQ_API_KEY`

### Step 6: Run the System
bash
python main.py


## 🚀 What Happens When You Run

1. **CEO Agent** receives the startup idea
2. **CEO** decomposes idea into tasks using Groq LLM
3. **Product Agent** generates detailed specification
4. **CEO** reviews spec (score 6/10 initially)
5. **Feedback Loop**: CEO requests revisions (3 cycles)
6. **Product Agent** improves spec based on feedback
7. **CEO** approves spec (score 7/10)
8. **Engineer Agent** creates GitHub PR with landing page
9. **Marketing Agent** sends email via SendGrid
10. **Marketing Agent** posts to Slack using Block Kit
11. **System completes** with all integrations verified

### Sample Output

🚀 CEO AGENT STARTING
💭 CEO: Decomposing startup idea into tasks...
📤 CEO: Sending task to Product Agent...
📋 PRODUCT: Generating product spec...
🔍 CEO: Reviewing product specification...
❌ CEO: Product spec REJECTED! (Score: 6/10)
📨 CEO -> PRODUCT: revision_request (Attempt 1)
✅ CEO: Product spec APPROVED after 3 revision(s)!
🔧 ENGINEER: Creating GitHub PR #55
📧 MARKETING: Sending email (SendGrid 202)
📢 MARKETING: Posting to Slack (Block Kit)
✅ SYSTEM EXECUTION COMPLETE!
```

## 📁 Project Structure

```
launchmind_cafe/
├── agents/
│   ├── ceo_agent.py          # Orchestrator with feedback loops
│   ├── product_agent.py      # Product spec generator
│   ├── engineer_agent.py     # GitHub integration
│   └── marketing_agent.py    # Email + Slack integration
├── main.py                   # Entry point
├── message_bus.py            # JSON message passing
├── requirements.txt          # Dependencies
├── .env.example             # Environment template
├── .gitignore               # Ignore sensitive files
└── README.md                # This file


## 🔗 Live Links

### GitHub
- **Repository:** https://github.com/Aaleenz/launchmind-campusfood-rescue
- **Latest PR:** https://github.com/Aaleenz/launchmind-campusfood-rescue/pull/55

### Slack Workspace
- **Channel:** #launches
- **Bot Name:** CampusFood Rescue Bot

### Demo Video
- **Link:** [Your YouTube/Google Drive link here]
- **Duration:** 8-10 minutes

---

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| Total agents | 4 (CEO, Product, Engineer, Marketing) |
| Feedback loop iterations | 3 |
| Score improvement | 6 → 7 (+1 point) |
| GitHub PR created | ✅ Yes (#55) |
| Slack posts | ✅ Yes (Block Kit format) |
| Emails sent | ✅ Yes (SendGrid 202) |
| Execution time | ~60 seconds |

---

## 🐛 Troubleshooting

### Issue: "GROQ_API_KEY not found"
**Solution:** Ensure `.env` file exists and contains `GROQ_API_KEY=your_key`

### Issue: GitHub PR not created
**Solution:** 
- Check `GITHUB_TOKEN` has `repo` scope
- Verify repository is public
- Run: `git remote -v` to check remote URL

### Issue: Slack message not appearing
**Solution:** 
- Verify bot is invited to #launches channel
- Check token has `chat:write` scope
- Run: `/invite @YourBotName` in #launches

### Issue: Email not sending
**Solution:**
- Verify SendGrid API key is active
- Confirm sender email is verified
- Check free tier limit (100 emails/day)

### Issue: Rate limit errors
**Solution:** System has built-in retry logic (3 attempts, exponential backoff)

---

## 📈 Future Improvements

- [ ] Add QA Agent for code review (bonus marks)
- [ ] Implement Redis pub/sub for message bus
- [ ] Add SMS integration via Twilio
- [ ] Deploy to cloud (AWS/GCP)
- [ ] Add web dashboard for monitoring
- [ ] Support multiple LLM providers (Claude, GPT-4)

---

## 👥 Group Members

| Name | Agent | Responsibilities |
|------|-------|------------------|
| Aaleen | CEO Agent | Orchestration, feedback loops, LLM prompts |
| Ayesha | Product Agent | Spec generation, revision handling |
| Aaleen | Engineer/Marketing | GitHub, Slack, Email integrations |

---

## 📚 Technologies Used

- **Python 3.8+** - Core language
- **Groq API** - LLM provider (Llama 3.1 8B)
- **GitHub API v3** - Repository management
- **Slack API** - Messaging with Block Kit
- **SendGrid API** - Email delivery
- **Threading** - Concurrent agent execution

---

## ✅ Assignment Requirements Met

- ✅ 4+ agents (CEO, Product, Engineer, Marketing)
- ✅ Real GitHub PR opened by Engineer agent
- ✅ Real Slack message with Block Kit formatting
- ✅ Real email via SendGrid API
- ✅ Dynamic feedback loop with CEO reasoning
- ✅ Structured JSON message passing
- ✅ LLM-powered agent decisions
- ✅ Clean code with environment variables
- ✅ Comprehensive README

---

## 🎓 Course Information

- **Course:** AGENTIC AI / MULTI-AGENT SYSTEMS
- **University:** FAST National University of Computer & Emerging Sciences
- **Assignment:** LaunchMind - Build a Startup Using AI Agents
- **Deadline:** 12th April 2026

---

## 📄 License

This project is submitted as academic work for FAST University. All rights reserved.

---

## 🙏 Acknowledgments

- FAST University faculty for the innovative assignment
- Groq for fast LLM inference
- Slack, GitHub, and SendGrid for free tier APIs

---

## 📧 Contact

For questions about this project:
- **GitHub Issues:** https://github.com/Aaleenz/launchmind-campusfood-rescue/issues
- **Slack:** #launches channel

---

**🎉 Built with 🤖 by Team LaunchMind Cafe**

*"Never let good food go to waste"*

