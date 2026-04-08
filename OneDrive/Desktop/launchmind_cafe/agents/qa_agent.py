import os
import json
import re
import time
import requests
from datetime import datetime

class QAAgent:
    def __init__(self, groq_client, message_bus):
        self.client = groq_client
        self.message_bus = message_bus
        self.agent_name = "qa"
        
    def extract_json(self, text: str) -> dict:
        """Extract JSON from LLM response"""
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix common issues
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                return json.loads(json_str)
        else:
            raise ValueError(f"No JSON object found in response: {text[:200]}")
    
    def call_llm_with_retry(self, prompt: str, max_retries: int = 3):
        """Call Groq API with exponential backoff retry logic"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                return response.choices[0].message.content
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1
                    print(f"   ⚠️ Rate limit hit, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    if attempt == max_retries - 1:
                        print(f"   ⚠️ LLM call failed after {max_retries} attempts: {e}")
                        return None
                    time.sleep(1)
        return None
    
    def run(self):
        """Main loop for QA agent"""
        print("🔍 QA AGENT STARTED - Waiting for review tasks...")
        
        while True:
            msg = self.message_bus.receive(self.agent_name)
            
            if msg:
                print(f"\n🔍 QA received: {msg['message_type']} from {msg['from_agent']}")
                
                if msg["message_type"] == "review_task":
                    self.review_outputs(msg)
                elif msg["message_type"] == "revision_request":
                    print(f"📝 QA: Received revision request - {msg['payload'].get('feedback', '')[:100]}...")
            
            time.sleep(0.5)
    
    def review_outputs(self, message):
        """Review Engineer's HTML and Marketing copy"""
        payload = message["payload"]
        html_content = payload.get("html_content", "")
        marketing_copy = payload.get("marketing_copy", {})
        product_spec = payload.get("product_spec", {})
        pr_url = payload.get("pr_url", "")
        repo_name = payload.get("repo_name", "")
        pr_number = payload.get("pr_number", "")
        qa_iteration = payload.get("qa_iteration", 1)
        
        print(f"\n🔍 QA: Reviewing outputs (Iteration {qa_iteration})...")
        
        # Review HTML (even if empty, provide meaningful feedback)
        html_review = self.review_html(html_content, product_spec)
        print(f"   📝 HTML Review Score: {html_review['score']}/10")
        if html_review.get('issues'):
            for issue in html_review['issues'][:2]:
                print(f"      - {issue}")
        
        # Review Marketing copy
        marketing_review = self.review_marketing(marketing_copy, product_spec)
        print(f"   📝 Marketing Review Score: {marketing_review['score']}/10")
        if marketing_review.get('issues'):
            for issue in marketing_review['issues'][:2]:
                print(f"      - {issue}")
        
        # Determine overall verdict (lower threshold for passing)
        overall_score = (html_review["score"] + marketing_review["score"]) / 2
        verdict = "PASS" if overall_score >= 6.0 else "FAIL"
        
        print(f"   🎯 Overall Score: {overall_score:.1f}/10 - {verdict}")
        
        # Post inline comments on GitHub PR (always post, not just on FAIL)
        if pr_url and pr_number and repo_name:
            self.post_github_inline_comments(
                repo_name=repo_name,
                pr_number=pr_number,
                html_content=html_content,
                html_review=html_review,
                marketing_review=marketing_review,
                verdict=verdict
            )
        
        # Send structured report back to CEO
        report = {
            "verdict": verdict,
            "overall_score": overall_score,
            "html_review": {
                "score": html_review.get("score", 0),
                "issues": html_review.get("issues", []),
                "recommendations": html_review.get("recommendations", [])
            },
            "marketing_review": {
                "score": marketing_review.get("score", 0),
                "issues": marketing_review.get("issues", []),
                "recommendations": marketing_review.get("recommendations", [])
            },
            "requires_revision": verdict == "FAIL",
            "parent_message_id": message["message_id"]
        }
        
        self.message_bus.send(
            from_agent=self.agent_name,
            to_agent="ceo",
            message_type="review_report",
            payload=report,
            parent_message_id=message["message_id"]
        )
        
        print(f"✅ QA: Review report sent to CEO")
        return report
    
    def review_html(self, html_content: str, product_spec: dict) -> dict:
        """Use LLM to review HTML against product spec"""
        
        # Handle empty HTML
        if not html_content or len(html_content) < 100:
            return {
                "score": 2,
                "issues": ["HTML content is missing or too short (needs at least 100 characters)", "Engineer agent may have failed to generate content"],
                "positive_points": [],
                "recommendations": ["Engineer agent must generate proper HTML landing page", "Check if LLM API is working correctly"]
            }
        
        prompt = f"""
You are a QA reviewer. Review this HTML landing page against the product specification.

PRODUCT SPEC:
- Value Proposition: {product_spec.get('value_proposition', 'N/A')[:200]}
- Features: {json.dumps(product_spec.get('features', [])[:2], indent=2)}

HTML CONTENT (first 3000 chars):
{html_content[:3000]}

Evaluate on these criteria (each 0-10):
1. Does the headline match the value proposition?
2. Are the core features mentioned or visible?
3. Is there a clear call-to-action button?
4. Is the design professional and readable?
5. Does it mention food waste or campus context?

Return your review as JSON:
{{
    "score": <average score 0-10>,
    "issues": ["issue1", "issue2", ...],
    "positive_points": ["good1", "good2", ...],
    "recommendations": ["fix1", "fix2", ...]
}}
"""
        
        try:
            content = self.call_llm_with_retry(prompt)
            if content:
                review = self.extract_json(content)
            else:
                raise ValueError("LLM returned None")
        except Exception as e:
            print(f"   ⚠️ HTML review failed: {e}")
            review = {
                "score": 5,
                "issues": ["Review failed - using default score"],
                "positive_points": [],
                "recommendations": ["Please ensure HTML content is generated properly"]
            }
        
        return review
    
    def review_marketing(self, marketing_copy: dict, product_spec: dict) -> dict:
        """Use LLM to review marketing copy"""
        
        if not marketing_copy or not marketing_copy.get('tagline'):
            return {
                "score": 3,
                "issues": ["Marketing copy is missing or incomplete"],
                "positive_points": [],
                "recommendations": ["Marketing agent must generate proper marketing materials"]
            }
        
        prompt = f"""
You are a QA reviewer. Review this marketing copy against the product specification.

PRODUCT SPEC:
- Value Proposition: {product_spec.get('value_proposition', 'N/A')[:200]}

MARKETING COPY:
- Tagline: {marketing_copy.get('tagline', 'N/A')}
- Description: {marketing_copy.get('description', 'N/A')[:200]}
- Email Subject: {marketing_copy.get('email_subject', 'N/A')}

Evaluate on these criteria (each 0-10):
1. Is the tagline compelling and under 10 words?
2. Does the description clearly explain the product?
3. Does the email have a clear call-to-action?
4. Is the tone appropriate for students?
5. Does the copy address food waste or savings?

Return your review as JSON:
{{
    "score": <average score 0-10>,
    "issues": ["issue1", "issue2", ...],
    "positive_points": ["good1", "good2", ...],
    "recommendations": ["fix1", "fix2", ...]
}}
"""
        
        try:
            content = self.call_llm_with_retry(prompt)
            if content:
                review = self.extract_json(content)
            else:
                raise ValueError("LLM returned None")
        except Exception as e:
            print(f"   ⚠️ Marketing review failed: {e}")
            review = {
                "score": 5,
                "issues": ["Review failed - using default score"],
                "positive_points": [],
                "recommendations": ["Please try again"]
            }
        
        return review
    
    def post_github_inline_comments(self, repo_name: str, pr_number: str, html_content: str, html_review: dict, marketing_review: dict, verdict: str):
        """
        Post inline comments on GitHub PR.
        This creates a proper PR review with inline comments on specific lines.
        """
        
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            print("   ⚠️ QA: No GITHUB_TOKEN found, skipping PR comments")
            return
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Step 1: Get the PR details to find the latest commit SHA
        pr_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"
        pr_response = requests.get(pr_url, headers=headers)
        
        if pr_response.status_code != 200:
            print(f"   ⚠️ QA: Failed to get PR details - {pr_response.status_code}")
            # Fallback to regular comment
            self.post_regular_comment(repo_name, pr_number, html_review, marketing_review, verdict, headers)
            return
        
        pr_data = pr_response.json()
        commit_sha = pr_data.get("head", {}).get("sha")
        
        if not commit_sha:
            print("   ⚠️ QA: Could not find commit SHA for inline comments")
            self.post_regular_comment(repo_name, pr_number, html_review, marketing_review, verdict, headers)
            return
        
        # Step 2: Get the file content to find line numbers for inline comments
        file_url = f"https://api.github.com/repos/{repo_name}/contents/index.html?ref={commit_sha}"
        file_response = requests.get(file_url, headers=headers)
        
        html_lines = []
        if file_response.status_code == 200:
            import base64
            content_encoded = file_response.json().get("content", "")
            if content_encoded:
                html_content_decoded = base64.b64decode(content_encoded).decode('utf-8')
                html_lines = html_content_decoded.split('\n')
        
        # Step 3: Create inline comments for specific issues
        comments = []
        
        # Add inline comments for HTML issues
        for issue in html_review.get('issues', [])[:3]:  # Max 3 inline comments
            # Find a relevant line number based on the issue
            line_num = self.find_relevant_line_number(issue, html_lines)
            
            comments.append({
                "path": "index.html",
                "position": line_num if line_num else 1,
                "body": f"🔍 **QA Issue:** {issue}\n\n💡 **Suggestion:** {self.get_suggestion_for_issue(issue)}"
            })
        
        # Step 4: Create the review with inline comments
        review_body = f"""## 🔍 QA Review Results - {verdict}

### Summary
- **HTML Score:** {html_review['score']}/10
- **Marketing Score:** {marketing_review['score']}/10  
- **Overall Score:** {(html_review['score'] + marketing_review['score']) / 2:.1f}/10

### Marketing Issues:
{chr(10).join(['- ' + issue for issue in marketing_review.get('issues', [])[:3]])}

### Top Recommendations:
{chr(10).join(['- ' + rec for rec in html_review.get('recommendations', [])[:2] + marketing_review.get('recommendations', [])[:2]])}

---
*🤖 This review was automatically generated by the LaunchMind QA Agent*
"""
        
        review_data = {
            "commit_id": commit_sha,
            "body": review_body,
            "event": "COMMENT",
            "comments": comments
        }
        
        # Step 5: Post the review
        review_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/reviews"
        
        try:
            response = requests.post(review_url, headers=headers, json=review_data)
            if response.status_code == 201:
                print(f"   ✅ QA: Posted INLINE review comment on PR #{pr_number} ({len(comments)} inline comments)")
                for comment in comments:
                    print(f"      - Line {comment['position']}: {comment['body'][:80]}...")
            else:
                print(f"   ⚠️ QA: Failed to post inline review - {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                # Fallback to regular comment
                self.post_regular_comment(repo_name, pr_number, html_review, marketing_review, verdict, headers)
        except Exception as e:
            print(f"   ⚠️ QA: Could not post GitHub review - {e}")
            self.post_regular_comment(repo_name, pr_number, html_review, marketing_review, verdict, headers)
    
    def find_relevant_line_number(self, issue: str, html_lines: list) -> int:
        """Find a relevant line number in the HTML file for an issue"""
        
        issue_lower = issue.lower()
        
        # Map issues to line patterns
        patterns = {
            "headline": ["<h1", "hero", "headline"],
            "features": ["feature", "feature-card", "features"],
            "cta": ["call-to-action", "cta", "btn", "button"],
            "design": ["style", "css", "responsive"],
            "food waste": ["food", "waste", "campus", "discount"]
        }
        
        for key, keywords in patterns.items():
            if key in issue_lower or any(kw in issue_lower for kw in keywords):
                for i, line in enumerate(html_lines, 1):
                    if any(kw in line.lower() for kw in keywords):
                        return i
        
        # Default to line 10 if no match found
        return 10
    
    def get_suggestion_for_issue(self, issue: str) -> str:
        """Generate a suggestion based on the issue type"""
        
        issue_lower = issue.lower()
        
        if "headline" in issue_lower or "headline" in issue_lower:
            return "Update the H1 tag to clearly state the value proposition (e.g., 'Never Let Good Food Go to Waste')"
        elif "feature" in issue_lower:
            return "Ensure all key features from the product spec are visible and clearly described"
        elif "cta" in issue_lower or "call-to-action" in issue_lower:
            return "Add a prominent call-to-action button (e.g., 'Sign Up for Alerts' or 'Get Started')"
        elif "design" in issue_lower or "professional" in issue_lower:
            return "Improve CSS styling: add better spacing, colors, and responsive design"
        elif "food waste" in issue_lower or "campus" in issue_lower:
            return "Add specific references to campus context and food waste reduction"
        else:
            return "Please review the product specification and ensure alignment"
    
    def post_regular_comment(self, repo_name: str, pr_number: str, html_review: dict, marketing_review: dict, verdict: str, headers: dict):
        """Fallback: Post a regular comment (not inline)"""
        
        comment_body = f"""## 🔍 QA Review Results - {verdict}

### HTML Issues:
{chr(10).join(['- ' + issue for issue in html_review.get('issues', [])[:3]])}

### Marketing Issues:
{chr(10).join(['- ' + issue for issue in marketing_review.get('issues', [])[:3]])}

### Top Recommendations:
{chr(10).join(['- ' + rec for rec in html_review.get('recommendations', [])[:2] + marketing_review.get('recommendations', [])[:2]])}

**Overall Score: {(html_review['score'] + marketing_review['score']) / 2:.1f}/10**

---
*🤖 This review was automatically generated by the LaunchMind QA Agent*
"""
        
        try:
            comment_url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
            response = requests.post(comment_url, headers=headers, json={"body": comment_body})
            if response.status_code == 201:
                print(f"   ✅ QA: Posted regular comment on PR #{pr_number}")
            else:
                print(f"   ⚠️ QA: Failed to post comment - {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ QA: Could not post GitHub comment - {e}")