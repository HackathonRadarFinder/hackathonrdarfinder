import { BrowserRouter } from 'react-router-dom';
import DemoApp from './demo/App';
import { ThemeProvider } from './demo/ThemeContext';
import './demo/styles.css';
import './demo/demo-notice.css';
export default function DemoPlatform() {
  return <ThemeProvider><BrowserRouter basename="/demo">
    <div className="demo-notice" role="note"><strong>Design demo · fictional data</strong>
      <span>Events, predictions, metrics and admin actions are simulated. No registrations or emails are sent. Changes reset on reload.</span>
      <a href="/">Open live portal</a></div>
    <DemoApp />
  </BrowserRouter></ThemeProvider>;
}
