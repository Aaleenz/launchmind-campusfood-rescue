import os
import json
import base64
import requests
import time
from groq import Groq
from groq import RateLimitError
from message_bus import message_bus

class EngineerAgent:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found!")
        
        self.client = Groq(api_key=api_key)
        self.github_token = os.environ.get("GITHUB_TOKEN")
        self.repo_name = "Aaleenz/launchmind-campusfood-rescue"
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github+json"
        }
        self.generated_html = None
    
    def call_llm_with_retry(self, prompt: str, max_retries: int = 5) -> str:
        """Call Groq API with exponential backoff for rate limits"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            except RateLimitError as e:
                # Extract wait time from error message if possible
                wait_time = 10  # Default wait time
                error_msg = str(e)
                if "try again in" in error_msg:
                    import re
                    match = re.search(r"try again in ([\d.]+)s", error_msg)
                    if match:
                        wait_time = float(match.group(1)) + 1
                
                print(f"   ⚠️ Rate limit hit (attempt {attempt+1}/{max_retries}), waiting {wait_time}s...")
                time.sleep(wait_time)
            except Exception as e:
                print(f"   ⚠️ API error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    raise
        
        raise Exception(f"Failed after {max_retries} retries")
    
    def generate_landing_page(self, product_spec: dict) -> str:
        """Generate HTML with retry logic"""
        prompt = f"""
        Create a complete HTML landing page for CampusFood Rescue based on this product spec:
        
        {json.dumps(product_spec, indent=2)}
        
        The landing page must include:
        - Hero section with headline and tagline
        - Features section (show the top 3 features)
        - How it works section
        - Call-to-action button (email signup or SMS alert signup)
        - Responsive design with modern CSS
        - Mobile-friendly
        
        Return ONLY the complete HTML/CSS code (no explanations, no markdown).
        """
        
        print("🔧 ENGINEER: Generating HTML landing page...")
        
        try:
            content = self.call_llm_with_retry(prompt)
            
            # Clean up markdown code blocks if present
            html = content
            if html.startswith("```html"):
                html = html[7:]
            if html.startswith("```"):
                html = html[3:]
            if html.endswith("```"):
                html = html[:-3]
            
            # Store for later use
            self.generated_html = html.strip()
            print(f"   ✅ HTML generated ({len(self.generated_html)} characters)")
            return self.generated_html
            
        except Exception as e:
            print(f"   ❌ HTML generation failed: {e}")
            # Return a fallback HTML
            fallback_html = self.get_fallback_html()
            self.generated_html = fallback_html
            return fallback_html
    
    def get_fallback_html(self) -> str:
        """Return fallback HTML when API fails"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CampusFood Rescue - Save Food, Save Money</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
        .hero { background: linear-gradient(135deg, #2ecc71, #27ae60); color: white; padding: 80px 0; text-align: center; }
        .hero h1 { font-size: 3rem; margin-bottom: 20px; }
        .hero p { font-size: 1.2rem; margin-bottom: 30px; }
        .btn { display: inline-block; background: white; color: #27ae60; padding: 15px 30px; border-radius: 5px; text-decoration: none; font-weight: bold; }
        .features { padding: 60px 0; background: #f9f9f9; }
        .features h2 { text-align: center; margin-bottom: 40px; }
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; }
        .feature-card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .feature-card h3 { color: #2ecc71; margin-bottom: 15px; }
        .cta { background: #27ae60; color: white; text-align: center; padding: 60px 0; }
        .cta h2 { margin-bottom: 20px; }
        .cta .btn { background: white; color: #27ae60; }
        footer { background: #333; color: white; text-align: center; padding: 20px; }
        @media (max-width: 768px) { .hero h1 { font-size: 2rem; } }
    </style>
</head>
<body>
    <div class="hero">
        <div class="container">
            <h1>Never Let Good Food Go to Waste</h1>
            <p>Real-time SMS alerts for leftover campus cafeteria food at discounted prices</p>
            <a href="#" class="btn">Sign Up for Alerts</a>
        </div>
    </div>
    <div class="features">
        <div class="container">
            <h2>How It Works</h2>
            <div class="feature-grid">
                <div class="feature-card">
                    <h3>📱 Real-time SMS Alerts</h3>
                    <p>Get instant notifications when food becomes available at discounted prices</p>
                </div>
                <div class="feature-card">
                    <h3>💰 Save Money</h3>
                    <p>Enjoy meals at 30-50% off regular cafeteria prices</p>
                </div>
                <div class="feature-card">
                    <h3>🌱 Reduce Waste</h3>
                    <p>Help our campus reduce food waste by 40%</p>
                </div>
            </div>
        </div>
    </div>
    <div class="cta">
        <div class="container">
            <h2>Join CampusFood Rescue Today!</h2>
            <p>Be the first to know when food is available</p>
            <a href="#" class="btn">Get Started</a>
        </div>
    </div>
    <footer>
        <p>&copy; 2025 CampusFood Rescue - Saving Food, Saving Money</p>
    </footer>
</body>
</html>"""
    
    def create_github_issue(self, product_spec: dict) -> str:
        """Create GitHub issue"""
        url = f"https://api.github.com/repos/{self.repo_name}/issues"
        
        issue_data = {
            "title": "Initial Landing Page - CampusFood Rescue",
            "body": f"""
## Product Specification Summary
**Value Proposition:** {product_spec.get('value_proposition', 'N/A')[:200]}

**Top Features:**
{chr(10).join([f"- {f['name']}: {f['description'][:100]}" for f in product_spec.get('features', [])[:3]])}

## Engineer Task
Build a responsive landing page showcasing the product with signup functionality.
            """,
            "labels": ["enhancement", "landing-page"]
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=issue_data)
            if response.status_code == 201:
                return response.json()["html_url"]
            else:
                print(f"   ⚠️ Failed to create issue: {response.status_code}")
                return None
        except Exception as e:
            print(f"   ⚠️ Issue creation error: {e}")
            return None
    
    def get_main_branch_sha(self) -> str:
        """Get the SHA of the main branch"""
        url = f"https://api.github.com/repos/{self.repo_name}/git/refs/heads/main"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()["object"]["sha"]
        else:
            raise Exception(f"Failed to get main branch: {response.status_code}")
    
    def delete_branch_if_exists(self, branch_name: str):
        """Delete branch if it already exists"""
        url = f"https://api.github.com/repos/{self.repo_name}/git/refs/heads/{branch_name}"
        response = requests.delete(url, headers=self.headers)
        if response.status_code == 204:
            print(f"   Deleted existing branch: {branch_name}")
    
    def create_branch(self, branch_name: str, base_sha: str) -> bool:
        """Create a new branch"""
        url = f"https://api.github.com/repos/{self.repo_name}/git/refs"
        branch_data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }
        response = requests.post(url, headers=self.headers, json=branch_data)
        if response.status_code == 201:
            print(f"   ✅ Branch created: {branch_name}")
            return True
        else:
            print(f"   ❌ Failed to create branch: {response.status_code}")
            return False
    
    def commit_file(self, branch_name: str, file_path: str, content: str, commit_message: str) -> bool:
        """Commit a file to the branch"""
        url = f"https://api.github.com/repos/{self.repo_name}/contents/{file_path}"
        content_encoded = base64.b64encode(content.encode()).decode()
        
        commit_data = {
            "message": commit_message,
            "content": content_encoded,
            "branch": branch_name,
            "committer": {
                "name": "EngineerAgent",
                "email": "agent@launchmind.ai"
            }
        }
        
        response = requests.put(url, headers=self.headers, json=commit_data)
        if response.status_code in [200, 201]:
            print(f"   ✅ File committed: {file_path}")
            return True
        else:
            print(f"   ❌ Failed to commit: {response.status_code}")
            return False
    
    def create_pull_request(self, branch_name: str, title: str, body: str) -> tuple:
        """Create a pull request"""
        url = f"https://api.github.com/repos/{self.repo_name}/pulls"
        pr_data = {
            "title": title,
            "body": body,
            "head": branch_name,
            "base": "main"
        }
        
        response = requests.post(url, headers=self.headers, json=pr_data)
        if response.status_code == 201:
            pr_info = response.json()
            return pr_info["html_url"], pr_info["number"]
        else:
            print(f"   ❌ Failed to create PR: {response.status_code}")
            return None, None
    
    def run(self):
        print("\n🔧 ENGINEER AGENT: Waiting for task...")
        
        while True:
            msg = message_bus.receive("engineer")
            
            if not msg:
                time.sleep(0.5)
                continue
            
            if msg["message_type"] == "task":
                print(f"\n🔧 ENGINEER AGENT: Received task to build landing page")
                
                product_spec = msg["payload"].get("product_spec", {})
                
                # Generate HTML landing page (with retry)
                html = self.generate_landing_page(product_spec)
                
                # Create GitHub issue (optional, don't fail if it doesn't work)
                print("🔧 ENGINEER: Creating GitHub issue...")
                issue_url = self.create_github_issue(product_spec)
                if issue_url:
                    print(f"   ✅ Issue created: {issue_url}")
                else:
                    print(f"   ⚠️ Continuing without issue")
                
                # Setup branch
                branch_name = f"agent-landing-page-{int(time.time())}"
                
                pr_url = None
                pr_number = None
                
                try:
                    # Get main branch SHA
                    main_sha = self.get_main_branch_sha()
                    
                    # Delete branch if it exists
                    self.delete_branch_if_exists(branch_name)
                    
                    # Create new branch
                    if self.create_branch(branch_name, main_sha):
                        # Commit HTML file
                        if self.commit_file(branch_name, "index.html", html, "Add landing page for CampusFood Rescue"):
                            # Create PR
                            pr_title = "🚀 Initial Landing Page - CampusFood Rescue"
                            pr_body = f"Complete landing page for CampusFood Rescue with responsive design."
                            pr_url, pr_number = self.create_pull_request(branch_name, pr_title, pr_body)
                            
                            if pr_url:
                                print(f"   ✅ PR opened: {pr_url}")
                            else:
                                print(f"   ⚠️ PR creation failed, but HTML was generated")
                        else:
                            print(f"   ⚠️ Commit failed, but HTML was generated")
                    else:
                        print(f"   ⚠️ Branch creation failed, but HTML was generated")
                        
                except Exception as e:
                    print(f"   ⚠️ GitHub operation error: {e}")
                    print(f"   Continuing with HTML content only")
                
                # ALWAYS send results back to CEO with HTML content
                result = {
                    "pr_url": pr_url or "https://github.com/Aaleenz/launchmind-campusfood-rescue",
                    "issue_url": issue_url,
                    "branch": branch_name,
                    "pr_number": pr_number,
                    "html_content": html,  # CRITICAL: Always include the HTML
                    "status": "success" if pr_url else "partial_success"
                }
                
                message_bus.send("engineer", "ceo", "result", result, msg["message_id"])
                print(f"🔧 ENGINEER AGENT: Sent results to CEO (HTML length: {len(html)} chars)")
                break
            
            elif msg["message_type"] == "revision_request":
                print(f"\n🔧 ENGINEER: Received revision request")
                feedback = msg["payload"].get("feedback", "")
                issues = msg["payload"].get("issues", [])
                
                product_spec = msg["payload"].get("product_spec", {})
                if not product_spec:
                    product_spec = {"value_proposition": "CampusFood Rescue"}
                
                # Generate improved HTML
                revision_prompt = f"""
                REVISION REQUEST: Please fix these issues:
                {json.dumps(issues, indent=2)}
                
                Feedback: {feedback}
                
                Generate an improved HTML landing page addressing these issues.
                Keep it responsive and modern.
                """
                
                print(f"   🔧 ENGINEER: Regenerating HTML with fixes...")
                html = self.call_llm_with_retry(revision_prompt)
                
                # Clean up
                if html.startswith("```html"):
                    html = html[7:]
                if html.startswith("```"):
                    html = html[3:]
                if html.endswith("```"):
                    html = html[:-3]
                
                self.generated_html = html.strip()
                
                # Send revised result back to CEO
                result = {
                    "pr_url": msg["payload"].get("pr_url", "https://github.com/Aaleenz/launchmind-campusfood-rescue"),
                    "html_content": self.generated_html,
                    "status": "revised",
                    "revision_round": msg["payload"].get("revision_round", 1)
                }
                
                message_bus.send("engineer", "ceo", "result", result, msg["message_id"])
                print(f"   🔧 ENGINEER: Sent revised HTML to CEO (length: {len(self.generated_html)})")
                break