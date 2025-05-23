from flask import Flask, jsonify, request, render_template, redirect, url_for, make_response
from markupsafe import Markup
from xhtml2pdf import pisa
from io import BytesIO
import requests
import os
import markdown
import tempfile
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

api_key = os.getenv("API_KEY")

def query_mistral(prompt):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistral-saba-24b",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that reviews text for professional tone, relevant skills, and phrasing aligned with industry standards."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=data)
    print("Status code:", response.status_code)
    print("Response body:", response.text)

    try:
        response_json = response.json()
    except Exception as e:
        return f"Error parsing response JSON: {e}"

    if "choices" in response_json:
        return response_json["choices"][0]["message"]["content"]
    else:
        return f"API error or unexpected response: {response_json}"

@app.route("/api/suggestion/<user_input>", methods=['GET'])
def suggestion(user_input):
    prompt = f"Analyze this user input for job relevance, tone, and skill alignment:\n\n{user_input}"
    output = query_mistral(prompt)
    
    output_html = markdown.markdown(output)
    return output_html    

@app.route("/api/suggestionskill", methods=['POST'])
def suggestionskill():
    data=request.get_json()
    user_input=data.get('jobd','')
    prompt = f"Suggest and list skills required based on user input of job decsription:\n\n{user_input}"
    output = query_mistral(prompt)
    
    output_html = markdown.markdown(output)
    return output_html    

@app.route("/api/suggestionproject/<user_input>", methods=['GET'])
def suggestionproject(user_input):
    prompt = f"Suggest better wording for projects entered by user:\n\n{user_input}"
    output = query_mistral(prompt)
    
    output_html = markdown.markdown(output)
    return output_html  


user_data = {}


prompts = [
    {
        "step": 1,
        "prompt": "Enter Job Description:",
        "context": "This will help us in suggesting required skills.",
        "field": "jobd"
    },
    {
        "step": 2,
        "prompt": "Enter your full Name:",
        "context": "This will appear at the top of your resume.",
        "field": "name"
    },
    {
        "step": 3,
        "prompt": "Enter your Mobile Number:",
        "context": "This will be part of your contact information.",
        "field": "mobile"
    },
    {
        "step": 4,
        "prompt": "Enter your Email Id:",
        "context": "This will be part of your contact information.",
        "field": "email"
    },
    {
        "step": 5,
        "prompt": "Enter your LinkdIn account URL:",
        "context": "This will be part of your contact information.",
        "field": "linkdin"
    },
    {
        "step": 6,
        "prompt": "Write a brief Professional Summary:",
        "context": "Summarize your career goals and skills. Paraphrase to improve wording.",
        "field": "summary"
    },
    {
        "step": 7,
        "prompt": "Enter your highest Educational Qualification:",
        "context": "Include Degree, Institution, and Graduation Year.",
        "field": "education"
    },
    {
        "step": 8,
        "prompt": "Describe your most relevant Work Experience:",
        "context": "Include roles, companies and achievements.",
        "field": "experience"
    },
    {
        "step": 9,
        "prompt": "List your Top Skills (comma separated):",
        "context": "Specify your skills or ask for suggestions based on Job Description.",
        "field": "skills"
    },
    {
        "step": 10,
        "prompt": "Mention any notable Projects:",
        "context": "Briefly describe projects that showcase your abilities. Paraphrase to improve wording.",
        "field": "projects"
    }
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/prompt/<int:step>', methods=['GET'])
def get_prompt(step):
    if 1 <= step <= len(prompts):
        return jsonify(prompts[step-1])
    else:
        return jsonify({"error": "Invalid step"}), 400

@app.route('/api/save_response', methods=['POST'])
def save_response():
    data = request.json
    user_id = data.get("user_id")
    field = data.get("field")
    response = data.get("response")

    if not user_id or not field:
        return jsonify({"error": "Missing user_id or field"}), 400

    if user_id not in user_data:
        user_data[user_id] = {}

    user_data[user_id][field] = response

    return jsonify({"status": "success"})

@app.route('/api/generate_resume/<user_id>', methods=['GET'])
def generate_resume(user_id):
    if user_id not in user_data:
        return jsonify({"error": "User data not found"}), 404

    data = user_data[user_id]

    
    resume_html = render_template('resume_template.html', data=data)
    return jsonify({"resume_html": resume_html})

@app.route('/preview/<user_id>', methods=['GET','POST'])
def preview_resume(user_id):
    if user_id not in user_data:
        return "User data not found", 404
    data = user_data[user_id]
    rendered_resume = render_template('resume_template.html', data=data)
    return render_template('resume_preview.html', resume_html=Markup(rendered_resume), data=data,user_id=user_id)

@app.route('/download_resume/<user_id>')
def download_resume(user_id):
    if user_id not in user_data:
        return "User data not found", 404
    data = user_data[user_id]
    resume_html = render_template('resume_template.html', data=data)

    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(resume_html, dest=pdf)
    if pisa_status.err:
        return "Error generating PDF", 500

    pdf.seek(0)
    response = make_response(pdf.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=resume_{user_id}.pdf'
    return response

@app.route('/resume_content/<user_id>')
def resume_content(user_id):
    if user_id not in user_data:
        return "User data not found", 404
    return render_template('resume_template.html', data=user_data[user_id])

if __name__ == '__main__':
    app.run(debug=True)
