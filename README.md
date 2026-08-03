# Production Report Package

Ye folder pura workflow chalane ke liye zaroori sab files rakhta hai:
Excel se data padhna → MongoDB me save karna → GitHub Pages pe manifest ready karna →
email me sirf live link bhejna.

## Files

| File | Kaam |
|---|---|
| `production_analysis_mongodb.py` | Excel file padhta hai, records nikalta hai, MongoDB me save karta hai, aur `manifest_template.html` se ek `production_manifest.html` banata hai |
| `manifest_template.html` | Manifest ka HTML/CSS/JS template — is folder me hi rehna chahiye, `production_analysis_mongodb.py` aur `app.py` dono isko use karte hain |
| `app.py` | Flask web server — Render pe deploy karne ke liye. Har request pe MongoDB (Atlas) se **live latest data** khींchta hai aur manifest render kar deta hai. Data update hone pe re-deploy karne ki zaroorat nahi |
| `send_report_from_mongodb.py` | MongoDB se latest report ka metadata nikalta hai aur email me sirf live link ka button bhejta hai (koi attachment nahi) |
| `server.py` | **MCP server entrypoint** — poore workflow ko AI assistant (jaise Claude) ke liye tools ke roop me expose karta hai |
| `tools/` | MCP tool definitions — `excel_tools.py`, `report_tools.py`, `mongo_tools.py`, `email_tools.py`. Sab existing classes ko reuse karte hain, koi naya business logic nahi |
| `services/report_state.py` | In-memory state manager — `process_excel()` ka result baaki tools (jaise `get_summary()`) ke liye yahan store hota hai |
| `Procfile` | Render ko batata hai ki `app.py` ko kaise start karna hai |
| `requirements.txt` | Python packages jo install karni hain |
| `mcp_config.example.json` | Claude Desktop me MCP server register karne ka example config |
| `.vscode/launch.json` | VS Code me MCP server debug karne ki configuration |

## Setup (naye computer/server pe)

### 1. Python install karo (agar nahi hai)
[python.org](https://www.python.org/downloads/) se latest version le lo.

### 2. Is folder ko naye machine pe copy karo
Poora `production_report_package` folder as-is copy kar do.

### 3. Dependencies install karo
```bash
pip install -r requirements.txt --break-system-packages
```

### 4. Environment variables set karo

**Windows PowerShell:**
```powershell
$env:MONGO_URI='mongodb://localhost:27017/'
$env:SENDER_EMAIL='your-gmail@gmail.com'
$env:SENDER_PASSWORD='your-gmail-app-password'
$env:RECIPIENT_EMAIL='recipient@example.com'
$env:MANIFEST_URL='https://rahilkhan789.github.io/Product_report/'
```

**Mac/Linux:**
```bash
export MONGO_URI='mongodb://localhost:27017/'
export SENDER_EMAIL='your-gmail@gmail.com'
export SENDER_PASSWORD='your-gmail-app-password'
export RECIPIENT_EMAIL='recipient@example.com'
export MANIFEST_URL='https://rahilkhan789.github.io/Product_report/'
```

> Gmail App Password yahan se banao: https://myaccount.google.com/apppasswords
> (Normal Gmail password kaam nahi karega.)

### 5. MongoDB ka access confirm karo
- Agar MongoDB isi machine pe local install hai, to `mongodb://localhost:27017/` sahi hai
- Agar MongoDB Atlas (cloud) use kar rahe ho, to `MONGO_URI` ko apna Atlas connection string se replace karo

## Run karne ka order

### Naya Excel data process karna ho (naya month/report):
```bash
python production_analysis_mongodb.py
```
Ye Excel padh ke MongoDB me save karega aur `production_manifest.html` bhi bana dega.
`production_manifest.html` ko phir GitHub repo me `index.html` naam se upload kar do.

### Sirf email bhejni ho (MongoDB me pehle se latest data hai):
```bash
python send_report_from_mongodb.py
```
Ye email me sirf GitHub Pages wala live link bhejega — koi attachment ya static data nahi.

## Render pe live web server deploy karna (`app.py`)

Ye sabse aasan hai GitHub repo (`mongodb`, `production_analysis_mongodb.py`, `manifest_template.html`, `app.py`,
`requirements.txt`, `Procfile`) ke through:

### 1. Naya GitHub repo banao aur upload karo
Poora `production_report_package` folder (ya kam se kam `app.py`, `manifest_template.html`,
`requirements.txt`, `Procfile`) ek GitHub repo me push kar do.

### 2. Render pe naya Web Service banao
1. **render.com** → Dashboard → **New +** → **Web Service**
2. Apna GitHub repo connect karo
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. **Environment** tab me ye variables add karo:
   - `MONGO_URI` = apna MongoDB Atlas connection string (Atlas dashboard → Connect → Drivers se milega)
   - `MONGO_DB` = `production_db`
   - `MONGO_COLLECTION` = `production_records`
5. **Create Web Service** click karo — deploy shuru ho jayega

### 3. Live URL check karo
Deploy hone ke baad Render top pe URL dega, jaisa:
`https://your-app-name.onrender.com`

Isko browser me kholo — manifest live data ke saath dikhna chahiye. Har baar naya data
MongoDB me aane par, isi URL ko refresh karne se naya data khud dikh jayega (koi re-deploy
ya re-upload nahi karna).

### 4. Email script ko update karo
`send_report_from_mongodb.py` me `MANIFEST_URL` ko Render wale URL se replace kar do:
```powershell
$env:MANIFEST_URL='https://your-app-name.onrender.com'
```

> **Free tier note:** Render ka free instance inactivity pe spin down ho jata hai — pehli
> request 50 second tak slow ho sakti hai. Agar ye acceptable nahi hai, to paid instance
> use karo.

## MCP Server (AI assistant integration)

`server.py` poore workflow ko **MCP tools** ke roop me expose karta hai, taaki
Claude jaisa AI assistant seedha in operations ko call kar sake — koi business
logic duplicate nahi hai, sab kuch existing files (`production_analysis_mongodb.py`,
`send_report_from_mongodb.py`) ko reuse karta hai.

### Available Tools

| Tool | Kaam |
|---|---|
| `process_excel(file_path, worksheet_name)` | Excel load karke records nikalta hai, state me store karta hai |
| `get_summary()` | Total records/quantity/clients + priority-wise counts |
| `list_clients()` | Sabhi unique client names |
| `get_client_report(client_name)` | Ek client ke sab items, quantities, priorities |
| `get_highest_priority_jobs()` | Sirf Highest Priority records |
| `get_high_priority_jobs()` | Sirf High Priority records |
| `search_item(item_description)` | Item description me text search |
| `generate_manifest(output_path)` | Accordion HTML manifest banata hai |
| `generate_json(output_path)` | JSON file save karta hai |
| `save_to_mongodb()` | Current records ko MongoDB me save karta hai |
| `latest_report()` | MongoDB se latest saved report ka metadata |
| `send_email(manifest_path)` | Full report table wali email bhejta hai |
| `send_manifest_link()` | Sirf live link wali email bhejta hai |

**Note:** `process_excel()` ko pehle call karna zaroori hai un tools ke liye jo
current loaded data pe kaam karte hain (`get_summary`, `list_clients`, etc.) —
`latest_report()` aur `send_manifest_link()` iska apvaad hain, wo seedha
MongoDB se padhte hain.

### Setup

1. Dependencies install karo (upar wala `requirements.txt` step already MCP SDK include karta hai)
2. Environment variables set karo (upar wale hi — `MONGO_URI`, `SENDER_EMAIL`, etc.)

### Testing (MCP Inspector se)

```bash
mcp dev server.py
```

Ye ek browser-based Inspector kholega jaha aap har tool ko manually call
karke test kar sakte ho, bina kisi AI client ke.

### Claude Desktop me connect karna

1. `mcp_config.example.json` ko copy karo Claude Desktop ke config file me
   (`claude_desktop_config.json` — Claude Desktop Settings → Developer se path milega)
2. `args` me `server.py` ka **absolute path** apne machine ke hisaab se daalo
3. `env` me apne actual credentials/URIs bhar do
4. Claude Desktop restart karo — ab naya "production-report" MCP server available hoga

### VS Code me debug karna

`.vscode/launch.json` already configured hai — bas **Run and Debug** panel me
"Debug MCP Server (server.py)" ya "Debug MCP Server (Inspector via mcp dev)"
select karke F5 dabao. Pehle `env` values apne actual credentials se update kar lena.

### Example prompts (AI client me)

- "Process the Excel file at C:\path\to\monthly-production.xlsx and give me a summary"
- "List all clients in the current report"
- "Show me all highest priority jobs"
- "Search for items containing 'Smoke Detector'"
- "Save the current report to MongoDB"
- "What's in the latest report saved in MongoDB?"
- "Generate the manifest HTML file"
- "Send the manifest link via email"

## Notes
- `production_analysis_mongodb.py` me `file_path` variable ko apne Excel file ke actual path se update karna hoga
- `SENDER_PASSWORD` kabhi bhi code me hardcode mat karo — hamesha environment variable se hi lo
- Atlas use kar rahe ho to Atlas dashboard me **Network Access** me Render ka IP (ya `0.0.0.0/0` for testing) whitelist karna padega, warna connection fail hoga
