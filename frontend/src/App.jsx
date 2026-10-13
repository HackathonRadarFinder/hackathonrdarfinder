import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthProvider';
import LivePlatform from './LivePlatform';
export default function App() {
  return <BrowserRouter><AuthProvider><LivePlatform /></AuthProvider></BrowserRouter>;
}
