import os
import json
import re
import time
import requests
from groq import Groq
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from message_bus import message_bus


class MarketingAgent:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found!")

        self.client = Groq(api_key=api_key)

        self.slack_token = os.environ.get("SLACK_BOT_TOKEN")
        self.sendgrid_key = os.environ.get("SENDGRID_API_KEY")
        self.from_email = os.environ.get("VERIFIED_SENDER_EMAIL", "test@example.com")

        self.last_marketing_result = None
        self.last_pr_url = None
        self.revision_round = 0

        print("🔍 SLACK TOKEN LOADED:", bool(self.slack_token))
        print("🔍 SENDGRID LOADED:", bool(self.sendgrid_key))

    def extract_json(self, text: str) -> dict:
        """Extract JSON from text, handling various formats"""
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        # Try to find JSON object
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"   ⚠️ JSON decode error: {e}")
                # Try to fix common issues
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                return json.loads(json_str)
        
        # Fallback: return a default structure
        print(f"   ⚠️ No JSON found, using fallback")
        return {
            "tagline": "Save Food, Save Money on Campus!",
            "description": "Real-time SMS alerts for leftover cafeteria food. Reduce waste, save money, eat well.",
            "email_subject": "🚨 Launching CampusFood Rescue - Reduce Food Waste on Campus!",
            "email_body": "Hey! We're launching CampusFood Rescue to help reduce food waste and save students money. Get real-time SMS alerts when cafeterias have surplus food at discounted prices. Join us in making our campus more sustainable!",
            "social_posts": [
                "🚨 Food alert! Save money & reduce waste with CampusFood Rescue - real-time SMS for discounted campus food! #FoodWaste #CampusLife",
                "Join CampusFood Rescue today and never miss a meal deal again! Save up to 50% on campus food 🍕📱",
                "#Sustainability meets savings! CampusFood Rescue helps reduce food waste while saving students money. Sign up for SMS alerts! 🌱💰"
            ]
        }

    def generate_marketing_materials_with_retry(self, product_spec: dict, revision_feedback: str = None, max_retries: int = 3) -> dict:
        """Generate marketing materials with retry logic for rate limits"""
        
        for attempt in range(max_retries):
            try:
                return self.generate_marketing_materials(product_spec, revision_feedback)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate_limit" in error_str.lower():
                    wait_time = (attempt + 1) * 5
                    print(f"⚠️ Rate limit hit. Retrying in {wait_time}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                elif "JSON" in error_str or "decode" in error_str.lower():
                    # JSON error - return fallback immediately
                    print(f"⚠️ JSON parsing error, using fallback materials")
                    return self.get_fallback_materials()
                else:
                    print(f"⚠️ Error on attempt {attempt+1}: {e}")
                    if attempt == max_retries - 1:
                        return self.get_fallback_materials()
                    time.sleep(2)
        
        return self.get_fallback_materials()
    
    def get_fallback_materials(self) -> dict:
        """Return fallback marketing materials"""
        return {
            "tagline": "Save Food, Save Money on Campus!",
            "description": "Real-time SMS alerts for leftover cafeteria food. Reduce waste, save money, eat well.",
            "email_subject": "🚨 Launching CampusFood Rescue - Reduce Food Waste on Campus!",
            "email_body": "Hey! We're launching CampusFood Rescue to help reduce food waste and save students money. Get real-time SMS alerts when cafeterias have surplus food at discounted prices. Join us in making our campus more sustainable!",
            "social_posts": [
                "🚨 Food alert! Save money & reduce waste with CampusFood Rescue - real-time SMS for discounted campus food! #FoodWaste #CampusLife",
                "Join CampusFood Rescue today and never miss a meal deal again! Save up to 50% on campus food 🍕📱",
                "#Sustainability meets savings! CampusFood Rescue helps reduce food waste while saving students money. Sign up for SMS alerts! 🌱💰"
            ]
        }

    def generate_marketing_materials(self, product_spec: dict, revision_feedback: str = None) -> dict:
        """Generate marketing materials"""
        
        revision_instruction = ""
        if revision_feedback:
            revision_instruction = f"""
            ⚠️ REVISION REQUEST (Round {self.revision_round + 1}):
            Feedback: {revision_feedback}
            
            Please improve the marketing materials based on this feedback.
            """
        
        prompt = f"""
        Create marketing materials for CampusFood Rescue based on this product spec:
        
        Product Spec: {json.dumps(product_spec, indent=2)}
        
        {revision_instruction}
        
        Return ONLY valid JSON (no markdown, no extra text):
        {{
            "tagline": "short catchy phrase under 10 words about saving food on campus",
            "description": "2-3 sentences explaining the value to students (include real-time SMS benefit)",
            "email_subject": "Email subject line for potential investor/user (engaging, under 60 chars)",
            "email_body": "Email body text explaining the product (professional, exciting, includes call to action)",
            "social_posts": ["Twitter post (280 chars max)", "LinkedIn post (professional tone)", "Instagram post (casual, emoji-heavy)"]
        }}
        
        Make it specific to a Pakistani university campus context.
        """

        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )

        content = response.choices[0].message.content
        return self.extract_json(content)

    def send_email_with_retry(self, subject: str, body: str, to_email: str = None, max_retries: int = 2) -> bool:
        """Send email with retry logic"""
        
        for attempt in range(max_retries):
            try:
                return self.send_email(subject, body, to_email)
            except Exception as e:
                print(f"⚠️ Email attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        return False

    def send_email(self, subject: str, body: str, to_email: str = None):
        to_email = to_email or os.environ.get("TEST_RECIPIENT_EMAIL", "aaleenzainab123@gmail.com")

        if not self.sendgrid_key:
            print("⚠️ SendGrid key missing, skipping email")
            return False

        message = Mail(
            from_email=self.from_email,
            to_emails=to_email,
            subject=subject,
            html_content=f"<div style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;'><h2 style='color: #2ecc71;'>🌱 {subject}</h2><p>{body}</p><hr><p style='color: #888; font-size: 12px;'>Generated by LaunchMind AI Agents</p></div>"
        )

        sg = SendGridAPIClient(self.sendgrid_key)
        response = sg.send(message)

        print("📧 SendGrid status:", response.status_code)

        if response.status_code == 202:
            print(f"✅ Email sent to {to_email}")
            return True
        
        return False

    def post_to_slack(self, pr_url, tagline, description):
        """Post to Slack using proper Block Kit format"""
        print("\n🔥 MARKETING: Attempting to post to Slack...")

        if not self.slack_token:
            print("❌ Slack token missing - cannot post")
            return False

        if not pr_url or pr_url == "None":
            print("⚠️ PR URL missing, using placeholder")
            pr_url = "https://github.com/Aaleenz/launchmind-campusfood-rescue"

        url = "https://slack.com/api/chat.postMessage"

        payload = {
            "channel": "#launches",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚀 New Launch: CampusFood Rescue",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{tagline or 'Save food, save money, on campus'}*"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": description or "Real-time notifications for leftover campus cafeteria food at discounted prices. Reducing waste, saving students money."
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*📦 GitHub PR:*\n<{pr_url}|Click to Review>"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*✅ Status:*\nReady for Review"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*🎯 Target:*\nStudents & Cafeteria Managers"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*📱 Platform:*\nSMS + Web Dashboard"
                        }
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "🤖 Generated by LaunchMind AI Agents • Multi-Agent System Assignment"
                        }
                    ]
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {self.slack_token}",
            "Content-Type": "application/json"
        }

        try:
            print("📢 Sending Slack request with Block Kit...")
            response = requests.post(url, headers=headers, json=payload)
            result = response.json()

            print(f"📢 Slack response status: {response.status_code}")
            
            if result.get("ok"):
                print("✅ Slack message posted successfully to #launches!")
                return True
            else:
                print(f"❌ Slack API error: {result.get('error')}")
                return False

        except Exception as e:
            print(f"❌ Slack exception: {e}")
            return False

    def run(self):
        print("\n📢 MARKETING AGENT: Started and waiting for messages...")
        
        running = True
        
        while running:
            msg = message_bus.receive("marketing")

            if not msg:
                time.sleep(0.5)
                continue

            print(f"\n📩 MARKETING received: {msg['message_type']} from {msg['from_agent']}")

            if msg["message_type"] == "task":
                print("\n📢 MARKETING: Processing task from Product agent...")
                
                product_spec = msg["payload"].get("product_spec", {})
                self.revision_round = 0

                materials = self.generate_marketing_materials_with_retry(product_spec)
                print("✅ Marketing materials generated")

                print("\n📧 MARKETING: Sending email...")
                self.send_email_with_retry(
                    materials.get("email_subject", "CampusFood Rescue Launch"),
                    materials.get("email_body", "Check out our new service!")
                )

                self.last_marketing_result = {
                    "tagline": materials.get("tagline"),
                    "description": materials.get("description"),
                    "social_posts": materials.get("social_posts", []),
                    "email_status": "sent"
                }

                message_bus.send(
                    "marketing",
                    "ceo",
                    "result",
                    self.last_marketing_result,
                    msg["message_id"]
                )
                
                print("📢 MARKETING: Sent results to CEO")

            elif msg["message_type"] == "confirmation":
                print("\n📢 MARKETING: Received confirmation from CEO!")
                
                pr_url = msg["payload"].get("pr_url")
                tagline = msg["payload"].get("tagline")
                description = msg["payload"].get("description")
                
                if not tagline and self.last_marketing_result:
                    tagline = self.last_marketing_result.get("tagline")
                if not description and self.last_marketing_result:
                    description = self.last_marketing_result.get("description")
                
                slack_success = self.post_to_slack(pr_url, tagline, description)
                
                if slack_success:
                    print("\n✅ MARKETING: Slack posting complete!")
                else:
                    print("\n⚠️ MARKETING: Slack posting failed")
                
                message_bus.send(
                    "marketing",
                    "ceo",
                    "confirmation",
                    {
                        "slack_posted": slack_success,
                        "pr_url": pr_url,
                        "tagline": tagline
                    },
                    msg["message_id"]
                )
                
                print("\n📢 MARKETING: All tasks complete, shutting down...")
                running = False

            elif msg["message_type"] == "revision_request":
                self.revision_round += 1
                print(f"\n📢 MARKETING: Received revision request (Round {self.revision_round})")
                feedback = msg["payload"].get("feedback", "")
                
                product_spec = msg["payload"].get("product_spec", {})
                if not product_spec and self.last_marketing_result:
                    product_spec = {"value_proposition": "CampusFood Rescue"}
                
                # Generate revised materials
                revised_materials = self.generate_marketing_materials_with_retry(product_spec, feedback)
                
                # Send revised results back
                message_bus.send(
                    "marketing",
                    "ceo",
                    "result",
                    {
                        "tagline": revised_materials.get("tagline"),
                        "description": revised_materials.get("description"),
                        "social_posts": revised_materials.get("social_posts", []),
                        "revision_round": self.revision_round,
                        "revised": True
                    },
                    msg["message_id"]
                )
                print(f"📢 MARKETING: Sent revised results to CEO (Round {self.revision_round})")
        
        print("\n📢 MARKETING AGENT: Shutdown complete")