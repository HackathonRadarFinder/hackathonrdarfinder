import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { api } from './services/apiClient';

function CollegeResults() {
  const [search, setSearch] = useState('');
  const [state, setState] = useState('');
  const [district, setDistrict] = useState('');
  const [query, setQuery] = useState({ search: '', state: '', district: '', page: 1 });
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  useEffect(() => {
    const controller = new AbortController();
    api.institutionFacets('', controller.signal)
      .then(value => { if (!controller.signal.aborted) setStates(value.states); })
      .catch(() => {});
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setDistricts([]);
    if (state) api.institutionFacets(state, controller.signal)
      .then(value => { if (!controller.signal.aborted) setDistricts(value.districts); })
      .catch(() => {});
    return () => controller.abort();
  }, [state]);
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState(null);
  const key = JSON.stringify([query, revision]);
  useEffect(() => {
    const controller = new AbortController();
    api.adminInstitutions(query, controller.signal).then(data => {
      if (!controller.signal.aborted) setResult({ key, data });
    }).catch(error => {
      if (!controller.signal.aborted) setResult({ key, error });
    });
    return () => controller.abort();
  }, [query, revision, key]);
  const current = result?.key === key ? result : null;
  const data = current?.data;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  return <section aria-labelledby="college-directory-heading">
    <p><Link to="/admin">Administration</Link> / Colleges</p>
    <h1 id="college-directory-heading">Private college directory</h1>
    <p>Administrator-only review of original college records and their source-permission status. Public factual listings are tracked separately.</p>
    <form className="platform-filters" onSubmit={event => { event.preventDefault(); setQuery({ search: search.trim(), state, district, page: 1 }); }}>
      <label>College name<input name="college" maxLength={255} value={search} onChange={event => setSearch(event.target.value)} placeholder="Search colleges" /></label>
      <label>State<select value={state} onChange={event => { setState(event.target.value); setDistrict(''); }}><option value="">All states</option>{states.map(item => <option key={item} value={item}>{item}</option>)}</select></label>
      <label>District<select value={district} disabled={!state} onChange={event => setDistrict(event.target.value)}><option value="">All districts</option>{districts.map(item => <option key={item} value={item}>{item}</option>)}</select></label>
      <button type="submit">Search</button>
      <button type="button" onClick={() => { setSearch(''); setState(''); setDistrict(''); setQuery({ search: '', state: '', district: '', page: 1 }); }}>Clear filters</button>
    </form>
    {!current && <p role="status">Loading colleges…</p>}
    {current?.error && <div role="alert" className="platform-error"><p>{current.error.message}</p><button onClick={() => setRevision(value => value + 1)}>Try again</button></div>}
    {data && <>
      <p role="status"><strong>{data.total.toLocaleString()}</strong> colleges{query.state ? ` in ${query.state}` : ''}{query.search ? ' matching your search' : ''}</p>
      {data.data.length === 0 ? <p>No colleges match these filters.</p> : <div className="platform-table" role="region" aria-label="Private colleges" tabIndex={0}><table>
        <thead><tr><th scope="col">College</th><th scope="col">AISHE identifier</th><th scope="col">State</th><th scope="col">District</th><th scope="col">Category</th><th scope="col">Permission</th></tr></thead>
        <tbody>{data.data.map(row => <tr key={row.id}><td>{row.name}</td><td>{row.identifier}</td><td>{row.state}</td><td>{row.district || 'Not provided'}</td><td>{row.category}</td><td>{row.permission_status === 'awaiting_permission' ? 'Awaiting permission' : row.permission_status}</td></tr>)}</tbody>
      </table></div>}
      <nav className="platform-pagination" aria-label="College directory pages">
        <button disabled={query.page <= 1} onClick={() => setQuery(value => ({ ...value, page: value.page - 1 }))}>Previous</button>
        <span>Page {data.page} of {pages}</span>
        <button disabled={query.page >= pages} onClick={() => setQuery(value => ({ ...value, page: value.page + 1 }))}>Next</button>
      </nav>
    </>}
  </section>;
}

export default function AdminCollegeDirectory() {
  const { user } = useAuth();
  if (!user) return <section><h1>Private college directory</h1><p>Sign in with your administrator account to view colleges.</p><Link to="/login">Sign in</Link></section>;
  if (user.role !== 'administrator') return <section><h1>Administrator access required</h1><p>Your account cannot view the private college directory.</p></section>;
  return <CollegeResults key={user.id} />;
}
