# LIN-IN - LinkedIn Insights
Analyse your LinkedIn connections and messages with some simple data science.

Caution: this is a quick and dirty simple toy project. No warranty! 

## Features
Upload your LinkedIn data export to receive information about:

- Overview of all your connections
- Companies and positions of your connections
- How your profile developed over time
- A graph of your company network
- A graph of positions within your network
- Overview of all your messages

https://github.com/cronn/lin-in/assets/4086468/b597b62c-99b3-4d21-a443-f691700a9164

## Run Locally

Clone the project

```bash
  git clone https://github.com/benthecoder/linkedin-visualizer.git
```

Go to the project directory

```bash
  cd lin-in
```

### Using Docker

Build an Image

```bash
docker build -t lin-in:0.0.1 .
```

Run the Image

```bash
docker run -p 8501:8501 lin-in:0.0.1
```

The app is now live on http://localhost:8501/

### Using Conda

Create Conda environment

```bash
  conda create --name env_name python=3.12.1
```

Activate the environment

```bash
  conda activate env_name
```

Install requirements

```bash
  pip install -r requirements.txt
```

Run streamlit

```bash
  streamlit run app.py
```

### Using Poetry

first make sure you have python 3.12.1

```bash
  poetry install
```

```bash
  poetry run streamlit run app.py
```

## Credits

This is an extended fork of [Linkedin Visualizer](https://github.com/benthecoder/linkedin-visualizer), adding several new functions, extensions, dependency updates (python 12+) and further cleaning. Other sources used:
- [Linkedin Analysis](https://github.com/tavishcode/linkedin_analysis/tree/master)
- [Linkedin Network Visualization](https://github.com/Thanh-To/linkedin-network-visualization)
- [Plotly Docs](https://plotly.com/python/treemaps/)

