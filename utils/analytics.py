"""
Analytics tracking for BookCreatorAI SaaS
Supports multiple providers: Mixpanel, Amplitude, or custom
"""
import os
import json
from datetime import datetime
from functools import wraps

# Analytics configuration
ANALYTICS_ENABLED = os.environ.get('ANALYTICS_ENABLED', 'false').lower() == 'true'
MIXPANEL_TOKEN = os.environ.get('MIXPANEL_TOKEN', '')
AMPLITUDE_API_KEY = os.environ.get('AMPLITUDE_API_KEY', '')
GA_TRACKING_ID = os.environ.get('GA_TRACKING_ID', '')


class AnalyticsTracker:
    """Analytics tracker supporting multiple providers"""
    
    def __init__(self):
        self.enabled = ANALYTICS_ENABLED
        self.mixpanel = None
        self.amplitude = None
        
        if self.enabled:
            self._init_providers()
    
    def _init_providers(self):
        """Initialize analytics providers"""
        # Mixpanel
        if MIXPANEL_TOKEN:
            try:
                from mixpanel import Mixpanel
                self.mixpanel = Mixpanel(MIXPANEL_TOKEN)
                print("[Analytics] Mixpanel initialized")
            except ImportError:
                print("[Analytics] Mixpanel not installed. Run: pip install mixpanel")
        
        # Amplitude
        if AMPLITUDE_API_KEY:
            try:
                from amplitude import Amplitude
                self.amplitude = Amplitude(AMPLITUDE_API_KEY)
                print("[Analytics] Amplitude initialized")
            except ImportError:
                print("[Analytics] Amplitude not installed. Run: pip install amplitude-analytics")
    
    def identify(self, user_id, traits=None):
        """Identify a user with traits"""
        if not self.enabled:
            return
        
        traits = traits or {}
        traits['identified_at'] = datetime.utcnow().isoformat()
        
        # Mixpanel
        if self.mixpanel:
            try:
                self.mixpanel.people_set(str(user_id), traits)
            except Exception as e:
                print(f"[Analytics] Mixpanel identify error: {e}")
        
        # Log for debugging
        print(f"[Analytics] Identify user {user_id}: {traits}")
    
    def track(self, user_id, event, properties=None):
        """Track an event"""
        if not self.enabled:
            return
        
        properties = properties or {}
        properties['timestamp'] = datetime.utcnow().isoformat()
        
        # Mixpanel
        if self.mixpanel:
            try:
                self.mixpanel.track(str(user_id), event, properties)
            except Exception as e:
                print(f"[Analytics] Mixpanel track error: {e}")
        
        # Log for debugging
        print(f"[Analytics] Track {event} for user {user_id}: {properties}")
    
    def track_page_view(self, user_id, page, properties=None):
        """Track a page view"""
        props = properties or {}
        props['page'] = page
        self.track(user_id, 'Page View', props)
    
    def track_signup(self, user_id, method='email'):
        """Track user signup"""
        self.track(user_id, 'Sign Up', {'method': method})
        self.identify(user_id, {'signup_method': method})
    
    def track_login(self, user_id):
        """Track user login"""
        self.track(user_id, 'Login', {})
    
    def track_subscription(self, user_id, plan, action, amount=None):
        """Track subscription events"""
        props = {
            'plan': plan,
            'action': action  # 'started', 'upgraded', 'downgraded', 'cancelled', 'renewed'
        }
        if amount:
            props['amount'] = amount
        
        self.track(user_id, 'Subscription', props)
        
        if action == 'started':
            self.identify(user_id, {'plan': plan, 'is_paying': True})
        elif action == 'cancelled':
            self.identify(user_id, {'is_paying': False})
    
    def track_analysis(self, user_id, book_title, aspect, language='pt-pt'):
        """Track book analysis"""
        self.track(user_id, 'Book Analysis', {
            'book_title': book_title,
            'aspect': aspect,
            'language': language
        })
    
    def track_feature_use(self, user_id, feature):
        """Track feature usage"""
        self.track(user_id, 'Feature Used', {'feature': feature})
    
    def track_upgrade_prompt(self, user_id, feature, current_plan):
        """Track when user sees upgrade prompt"""
        self.track(user_id, 'Upgrade Prompt Shown', {
            'feature': feature,
            'current_plan': current_plan
        })
    
    def track_support_request(self, user_id, subject):
        """Track support request"""
        self.track(user_id, 'Support Request', {'subject': subject})


# Global tracker instance
tracker = AnalyticsTracker()


def get_analytics_scripts():
    """Get analytics script tags for templates"""
    scripts = []
    
    # Google Analytics
    if GA_TRACKING_ID:
        scripts.append(f"""
        <!-- Google Analytics -->
        <script async src="https://www.googletagmanager.com/gtag/js?id={GA_TRACKING_ID}"></script>
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){{dataLayer.push(arguments);}}
            gtag('js', new Date());
            gtag('config', '{GA_TRACKING_ID}');
        </script>
        """)
    
    # Mixpanel
    if MIXPANEL_TOKEN:
        scripts.append(f"""
        <!-- Mixpanel -->
        <script>
            (function(f,b){{if(!b.__SV){{var e,g,i,h;window.mixpanel=b;b._i=[];b.init=function(e,f,c){{function g(a,d){{var b=d.split(".");2==b.length&&(a=a[b[0]],d=b[1]);a[d]=function(){{a.push([d].concat(Array.prototype.slice.call(arguments,0)))}}}}var a=b;"undefined"!==typeof c?a=b[c]=[]:c="mixpanel";a.people=a.people||[];a.toString=function(a){{var d="mixpanel";"mixpanel"!==c&&(d+="."+c);a||(d+=" (stub)");return d}};a.people.toString=function(){{return a.toString(1)+".people (stub)"}};i="disable time_event track track_pageview track_links track_forms track_with_groups add_group set_group remove_group register register_once alias unregister identify name_tag set_config reset opt_in_tracking opt_out_tracking has_opted_in_tracking has_opted_out_tracking clear_opt_in_out_tracking start_batch_senders people.set people.set_once people.unset people.increment people.append people.union people.track_charge people.clear_charges people.delete_user people.remove".split(" ");for(h=0;h<i.length;h++)g(a,i[h]);var j="set set_once union unset remove delete".split(" ");a.get_group=function(){{function b(c){{d[c]=function(){{call2_args=arguments;call2=[c].concat(Array.prototype.slice.call(call2_args,0));a.push([e,call2])}}}}for(var d={{}},e=["get_group"].concat(Array.prototype.slice.call(arguments,0)),c=0;c<j.length;c++)b(j[c]);return d}};b._i.push([e,f,c])}};b.__SV=1.2;e=f.createElement("script");e.type="text/javascript";e.async=!0;e.src="undefined"!==typeof MIXPANEL_CUSTOM_LIB_URL?MIXPANEL_CUSTOM_LIB_URL:"file:"===f.location.protocol&&"//cdn.mxpnl.com/libs/mixpanel-2-latest.min.js".match(/^\\/\\//)?"https://cdn.mxpnl.com/libs/mixpanel-2-latest.min.js":"//cdn.mxpnl.com/libs/mixpanel-2-latest.min.js";g=f.getElementsByTagName("script")[0];g.parentNode.insertBefore(e,g)}}}})(document,window.mixpanel||[]);
            mixpanel.init('{MIXPANEL_TOKEN}', {{track_pageview: true}});
        </script>
        """)
    
    # Amplitude
    if AMPLITUDE_API_KEY:
        scripts.append(f"""
        <!-- Amplitude -->
        <script>
            !function(){{var e=window.amplitude||{{_q:[],_iq:{{}}}};if(e.invoked)window.console&&console.error&&console.error("Amplitude snippet has been loaded.");else{{e.invoked=!0;var t=document.createElement("script");t.type="text/javascript";t.integrity="sha384-PPfHw98myKtJkA9OdPBMQ6n8yvUaYk0EBPWvGpAzo8Oaknitm0oyiP/DQVBnLnyE";t.crossOrigin="anonymous";t.async=!0;t.src="https://cdn.amplitude.com/libs/analytics-browser-2.0.0-min.js.gz";t.onload=function(){{window.amplitude.init("{AMPLITUDE_API_KEY}",undefined,{{defaultTracking:{{pageViews:true,sessions:true,formInteractions:true,fileDownloads:true}}}});}};var s=document.getElementsByTagName("script")[0];s.parentNode.insertBefore(t,s);for(var n=function(){{return this._q.push(Array.prototype.slice.call(arguments))}},r=["add","append","clearAll","prepend","set","setOnce","unset","preInsert","postInsert","remove","getUserProperties"],o=0;o<r.length;o++){{var i=r[o];e.Identify.prototype[i]=n}}for(var a=function(){{this._q=[];return this}},c=["getEventProperties","setProductId","setQuantity","setPrice","setRevenue","setRevenueType","setEventProperties"],u=0;u<c.length;u++){{var l=c[u];a.prototype[l]=n}}e.Revenue=a;var p=["getDeviceId","setDeviceId","getSessionId","setSessionId","getUserId","setUserId","setOptOut","setTransport","reset","extendSession"],d=["init","add","remove","track","logEvent","identify","groupIdentify","setGroup","revenue","flush"];function v(t){{function n(n){{e[t]=function(){{if("init"===n)return e._q.unshift([t,n].concat(Array.prototype.slice.call(arguments)));e._q.push([t,n].concat(Array.prototype.slice.call(arguments)))}}}}for(var r=0;r<p.length;r++)n(p[r]);for(var o=0;o<d.length;o++)n(d[o])}}v("getInstance");e.init=function(t){{e._q.push(["init",t])}};window.amplitude=e}}}}();
        </script>
        """)
    
    return '\n'.join(scripts)


def get_user_analytics_identify(user):
    """Get JavaScript to identify user in analytics"""
    if not user or not user.is_authenticated:
        return ''
    
    scripts = []
    
    if MIXPANEL_TOKEN:
        scripts.append(f"""
        mixpanel.identify('{user.id}');
        mixpanel.people.set({{
            '$email': '{user.email}',
            '$name': '{user.name}',
            'plan': '{user.plan}',
            'signup_date': '{user.created_at.isoformat() if user.created_at else ""}'
        }});
        """)
    
    if AMPLITUDE_API_KEY:
        scripts.append(f"""
        amplitude.setUserId('{user.id}');
        amplitude.identify(new amplitude.Identify()
            .set('email', '{user.email}')
            .set('name', '{user.name}')
            .set('plan', '{user.plan}')
        );
        """)
    
    if scripts:
        return f"<script>{' '.join(scripts)}</script>"
    return ''
