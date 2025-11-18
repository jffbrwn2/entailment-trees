# Deployment Guide for Interactive Visualizer

This guide explains how to run the interactive visualizer locally and deploy it as a web app.

## Option 1: Run Locally with Pixi (Recommended)

If you're in the ai-simulations project with pixi set up:

```bash
# From the ai-simulations directory
pixi install
pixi run viz
```

The app will open in your browser at `http://localhost:8501`

## Option 2: Run Locally with Python/pip

If you prefer using standard Python:

```bash
cd ultrasound_eeg_enhancement

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run interactive_visualizer.py
```

The app will open in your browser at `http://localhost:8501`

## Option 3: Deploy to Streamlit Community Cloud (Free!)

Streamlit Community Cloud allows you to deploy and share your app for free:

### Steps:

1. **Push code to GitHub:**
   ```bash
   # Make sure your repository is up to date
   git add .
   git commit -m "Add interactive visualizer"
   git push
   ```

2. **Go to Streamlit Community Cloud:**
   - Visit: https://streamlit.io/cloud
   - Sign in with your GitHub account

3. **Deploy new app:**
   - Click "New app"
   - Select your repository: `alegria/ai-simulations`
   - Set branch: `main` (or your current branch)
   - Set main file path: `ultrasound_eeg_enhancement/interactive_visualizer.py`
   - Click "Deploy"

4. **Wait for deployment:**
   - Streamlit will install dependencies from `requirements.txt`
   - Takes 2-5 minutes for first deployment
   - You'll get a URL like: `https://your-app-name.streamlit.app`

5. **Share the URL:**
   - Anyone can access the app via the URL
   - No login required for viewers
   - App stays live as long as it's accessed occasionally

### Streamlit Cloud Limits (Free Tier):
- 1 GB memory
- 1 CPU core
- Unlimited public apps
- Apps sleep after inactivity (wake up on access)

These limits are more than sufficient for this visualizer!

## Option 4: Deploy to Other Platforms

### Hugging Face Spaces (Free)

1. Create a new Space at https://huggingface.co/spaces
2. Choose "Streamlit" as the SDK
3. Upload files:
   - `interactive_visualizer.py`
   - `requirements.txt`
4. The app will auto-deploy

### Render (Free tier available)

1. Create account at https://render.com
2. New Web Service → Deploy from GitHub
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `streamlit run interactive_visualizer.py --server.port=$PORT --server.address=0.0.0.0`

### Railway (Free trial)

1. Create account at https://railway.app
2. New Project → Deploy from GitHub
3. Add start command: `streamlit run interactive_visualizer.py`

## Spinning Up Multiple Instances

You can easily create multiple instances to share with different people or for different parameter explorations:

### Why multiple instances?

- Share different preset configurations
- Allow concurrent exploration without conflicts
- Create specialized versions for different audiences

### How to spin up multiple:

**On Streamlit Cloud:**
1. Each GitHub branch can have its own deployment
2. Create branches like `viz-conservative`, `viz-optimistic`
3. Deploy each branch separately
4. Each gets its own URL

**Locally:**
```bash
# Terminal 1
streamlit run interactive_visualizer.py --server.port 8501

# Terminal 2
streamlit run interactive_visualizer.py --server.port 8502

# Terminal 3
streamlit run interactive_visualizer.py --server.port 8503
```

Access each at different ports:
- http://localhost:8501
- http://localhost:8502
- http://localhost:8503

## Customization

### Change default parameters:

Edit the `value=` parameters in the sliders in `interactive_visualizer.py`:

```python
P_acoustic_MPa = st.sidebar.slider(
    "Pressure (MPa)",
    min_value=0.5,
    max_value=3.0,
    value=2.0,  # ← Change this default
    step=0.1,
)
```

### Add new visualizations:

Add new tabs or plots in the visualization section around line 400+.

### Modify styling:

Edit the CSS in the `st.markdown("""<style>...</style>""")` section at the top.

## Troubleshooting

### Port already in use:
```bash
# Specify different port
streamlit run interactive_visualizer.py --server.port 8502
```

### Dependencies not found:
```bash
# Reinstall
pip install -r requirements.txt --force-reinstall
```

### Streamlit won't start:
```bash
# Clear cache
streamlit cache clear
```

### Deployment fails on Streamlit Cloud:
- Check that `requirements.txt` is in the same directory as the Python file
- Make sure repository is public or you've granted access
- Check the build logs for specific errors

## Performance Notes

The app is highly interactive and recalculates everything on parameter changes. This is fast for the current analytical model, but if you extend it to full 2D simulations, consider:

1. **Caching:** Use `@st.cache_data` decorator for expensive computations
2. **Progressive rendering:** Show results incrementally
3. **Backend compute:** Move heavy simulations to separate backend service

## Security Notes

- The app runs computation client-side (in the Python backend, not browser)
- No user data is stored
- All parameters are validated before use
- Safe for public deployment

## Support

For issues:
1. Check the Streamlit docs: https://docs.streamlit.io
2. Streamlit forum: https://discuss.streamlit.io
3. Project README: See assumptions and limitations

Enjoy exploring the parameter space! 🧠🔊
