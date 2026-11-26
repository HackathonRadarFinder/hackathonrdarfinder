import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');

const curatedPath = path.join(rootDir, 'backend', 'data', 'curated-mvp-20261013.json');
let rawEvents = [];
try {
  rawEvents = JSON.parse(fs.readFileSync(curatedPath, 'utf8'));
} catch (e) {
  console.error('Failed to read curated events', e);
}

// Sample supplemental events so the catalog is rich and diverse
const sampleEvents = [
  {
    title: "Google Solution Challenge 2027",
    organization: "Google Developer Groups",
    source: "Official Google Developers",
    url: "https://developers.google.com",
    location: "Online / Global",
    mode: "Online",
    start_date: "2027-01-18T10:00:00Z",
    end_date: "2027-03-15T18:00:00Z",
    registration_deadline: "2027-03-01T23:59:00Z",
    prize: "$10,000 USD + Mentorship",
    description: "Build cutting-edge solutions addressing UN Sustainable Development Goals using Google Cloud, Vertex AI, and Android.",
    scraped_at: new Date().toISOString()
  },
  {
    title: "Microsoft Imagine Cup 2027",
    organization: "Microsoft",
    source: "Official Microsoft Student Hub",
    url: "https://imaginecup.microsoft.com",
    location: "Hybrid / Redmond, WA",
    mode: "Hybrid",
    start_date: "2027-02-01T09:00:00Z",
    end_date: "2027-04-30T17:00:00Z",
    registration_deadline: "2027-01-25T23:59:00Z",
    prize: "$100,000 USD + Azure Credits",
    description: "Global student technology competition empowering next-generation founders to bring purpose-driven tech ventures to life.",
    scraped_at: new Date().toISOString()
  },
  {
    title: "Smart India Hackathon 2027",
    organization: "Government of India",
    source: "Ministry of Education Innovation Cell",
    url: "https://sih.gov.in",
    location: "New Delhi, India",
    mode: "Hybrid",
    start_date: "2027-03-10T04:30:00Z",
    end_date: "2027-03-12T12:30:00Z",
    registration_deadline: "2027-02-28T18:29:00Z",
    prize: "₹1,00,000 per problem statement",
    description: "World's biggest open innovation model bringing college students together to solve pressing governance and societal challenges.",
    scraped_at: new Date().toISOString()
  },
  {
    title: "NVIDIA Generative AI Hackathon",
    organization: "NVIDIA",
    source: "NVIDIA Developer Community",
    url: "https://developer.nvidia.com",
    location: "Online",
    mode: "Online",
    start_date: "2027-02-14T08:00:00Z",
    end_date: "2027-02-28T20:00:00Z",
    registration_deadline: "2027-02-12T23:59:00Z",
    prize: "NVIDIA RTX 5090 GPUs + $50K",
    description: "Push the boundaries of Generative AI inference and training using NVIDIA NIMs, CUDA, and TensorRT-LLM frameworks.",
    scraped_at: new Date().toISOString()
  },
  {
    title: "AWS GenAI Builder Challenge",
    organization: "Amazon Web Services",
    source: "AWS Community",
    url: "https://aws.amazon.com",
    location: "Online",
    mode: "Online",
    start_date: "2027-03-01T09:00:00Z",
    end_date: "2027-03-20T17:00:00Z",
    registration_deadline: "2027-02-26T23:59:00Z",
    prize: "$40,000 in AWS Credits",
    description: "Architect agentic workflows and multimodal applications powered by Amazon Bedrock, Anthropic Claude, and Amazon Q.",
    scraped_at: new Date().toISOString()
  },
  {
    title: "Meta Llama Open Challenge",
    organization: "Meta",
    source: "Meta Open Source",
    url: "https://ai.meta.com",
    location: "Menlo Park, CA / Remote",
    mode: "Hybrid",
    start_date: "2027-04-05T10:00:00Z",
    end_date: "2027-04-18T18:00:00Z",
    registration_deadline: "2027-03-31T23:59:00Z",
    prize: "$75,000 Cash Pool",
    description: "Build transformative open-source AI applications leveraging Llama 3 models across edge, mobile, and cloud environments.",
    scraped_at: new Date().toISOString()
  }
];

const allEventsData = [...rawEvents, ...sampleEvents];

const orgSet = new Set(allEventsData.map(e => e.organization).filter(Boolean));
const organizations = Array.from(orgSet).map((name, index) => ({ id: index + 1, name }));
const orgNameToId = new Map(organizations.map(o => [o.name, o.id]));

const events = allEventsData.map((e, index) => ({
  id: index + 1,
  title: e.title,
  organization_id: orgNameToId.get(e.organization) || 1,
  source: e.source || "Official website",
  url: e.url || null,
  registration_url: e.url || null,
  location: e.location || "Online",
  mode: e.mode || "Online",
  start_date: e.start_date || null,
  end_date: e.end_date || null,
  registration_deadline: e.registration_deadline || null,
  prize: e.prize || "Not provided",
  description: e.description || "",
  scraped_at: e.scraped_at || new Date().toISOString(),
  state: e.location?.includes('India') ? "Telangana" : null,
  acquisition: "Curated & Verified"
}));

const sampleInstitutions = [
  { id: 1, name: "Indian Institute of Technology, Hyderabad", state: "Telangana", city: "Sangareddy", category: "Institute of National Importance", identifier: "IIT-HYD", website: "https://www.iith.ac.in", source_url: "https://www.iith.ac.in", last_verified_at: new Date().toISOString() },
  { id: 2, name: "International Institute of Information Technology, Hyderabad", state: "Telangana", city: "Hyderabad", category: "Deemed University", identifier: "IIIT-HYD", website: "https://www.iiit.ac.in", source_url: "https://www.iiit.ac.in", last_verified_at: new Date().toISOString() },
  { id: 3, name: "Harvard University", state: "Massachusetts", city: "Cambridge", category: "University", identifier: "HARVARD", website: "https://www.harvard.edu", source_url: "https://www.harvard.edu", last_verified_at: new Date().toISOString() },
  { id: 4, name: "Massachusetts Institute of Technology", state: "Massachusetts", city: "Cambridge", category: "University", identifier: "MIT", website: "https://www.mit.edu", source_url: "https://www.mit.edu", last_verified_at: new Date().toISOString() },
  { id: 5, name: "Stanford University", state: "California", city: "Stanford", category: "University", identifier: "STANFORD", website: "https://www.stanford.edu", source_url: "https://www.stanford.edu", last_verified_at: new Date().toISOString() }
];

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || '127.0.0.1:8000'}`);
  const pathname = url.pathname;
  const searchParams = url.searchParams;

  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  function sendJson(status, data) {
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(data));
  }

  // Routes
  if (pathname === '/organizations' || pathname === '/organizations/') {
    sendJson(200, { data: organizations });
    return;
  }

  if (pathname === '/institutions' || pathname === '/institutions/') {
    const q = searchParams.get('q')?.toLowerCase() || '';
    const state = searchParams.get('state')?.toLowerCase() || '';
    const filtered = sampleInstitutions.filter(inst => {
      if (q && !inst.name.toLowerCase().includes(q)) return false;
      if (state && !inst.state.toLowerCase().includes(state)) return false;
      return true;
    });
    sendJson(200, { data: filtered, total: filtered.length, page: 1, page_size: 100 });
    return;
  }

  if (pathname === '/events' || pathname === '/events/') {
    const q = searchParams.get('q')?.toLowerCase() || '';
    const mode = searchParams.get('mode')?.toLowerCase() || '';
    const location = searchParams.get('location')?.toLowerCase() || '';
    const orgId = searchParams.get('organization_id');
    const page = parseInt(searchParams.get('page') || '1', 10);
    const pageSize = parseInt(searchParams.get('page_size') || '12', 10);

    let filtered = events.filter(e => {
      if (q && !(e.title.toLowerCase().includes(q) || e.description.toLowerCase().includes(q))) return false;
      if (mode && !e.mode.toLowerCase().includes(mode)) return false;
      if (location && !e.location.toLowerCase().includes(location)) return false;
      if (orgId && String(e.organization_id) !== String(orgId)) return false;
      return true;
    });

    const start = (page - 1) * pageSize;
    const paginated = filtered.slice(start, start + pageSize);

    sendJson(200, {
      data: paginated,
      total: filtered.length,
      page,
      page_size: pageSize
    });
    return;
  }

  const eventMatch = pathname.match(/^\/events\/(\d+)$/);
  if (eventMatch) {
    const id = parseInt(eventMatch[1], 10);
    const event = events.find(e => e.id === id);
    if (!event) {
      sendJson(404, { detail: 'Event not found', request_id: 'dev-mock-404' });
    } else {
      sendJson(200, { data: event });
    }
    return;
  }

  const discoveryMatch = pathname.match(/^\/events\/(\d+)\/discovery$/);
  if (discoveryMatch) {
    sendJson(200, {
      data: {
        evidence: [
          { source: "Official website crawler", observed_at: new Date().toISOString(), adapter_version: "v2.4" }
        ],
        versions: []
      }
    });
    return;
  }

  if (pathname === '/predictions/catalog' || pathname === '/predictions/catalog/') {
    sendJson(200, { data: [] });
    return;
  }

  if (pathname === '/predictions/readiness' || pathname === '/predictions/readiness/') {
    sendJson(200, {
      data: {
        reviewed_editions: events.length,
        recurring_series: 4,
        reason: "Active baseline calibration in progress."
      }
    });
    return;
  }

  if (pathname === '/admin/stats') {
    sendJson(200, {
      total_events: events.length,
      organizations: organizations.length,
      verified_sources: 12
    });
    return;
  }

  if (pathname === '/admin/users') {
    sendJson(200, { data: [] });
    return;
  }

  if (pathname === '/admin/organizations') {
    sendJson(200, { data: organizations });
    return;
  }

  if (pathname === '/account/saved') {
    sendJson(200, { data: [] });
    return;
  }

  if (pathname === '/notifications' || pathname === '/notifications/') {
    sendJson(200, { data: [] });
    return;
  }

  if (pathname === '/ready' || pathname === '/health') {
    sendJson(200, { status: "ready" });
    return;
  }

  sendJson(404, { detail: "Not found", request_id: "dev-404" });
});

const PORT = 8000;
server.listen(PORT, '127.0.0.1', () => {
  console.log(`Development API server running at http://127.0.0.1:${PORT}`);
});
