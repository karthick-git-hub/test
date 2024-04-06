from setuptools import setup, find_packages

setup(
    name="sequence",
    version="0.6.2",
    author="Xiaoliang Wu, Joaquin Chung, Alexander Kolar, Alexander Kiefer, Eugene Wang, Tian Zhong, Rajkumar Kettimuthu, Martin Suchara",
    author_email="xwu64@hawk.iit.edu, chungmiranda@anl.gov, akolar@anl.gov, akiefer@iu.edu, eugenewang@yahoo.com, tzh@uchicago.edu, kettimut@mcs.anl.gov, msuchara@anl.gov",
    description="Simulator of Quantum Network Communication: SEQUENCE-Python is a prototype version of the official SEQUENCE release.",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        'sequence': [
            'gui/user_templates.json',
            'gui/default_params.json',
            'gui/starlight.json'
        ]
    },
    include_package_data=True,
    install_requires=[
        'numpy>=1.22',
        'matplotlib',
        'pandas',
        'qutip>=4.6.0',
        'dash>=1.20.0',
        'dash-core-components',
        'dash-html-components',
        'dash-bootstrap-components',
        'tqdm>=4.54.0',
        'networkx',
        'dash-table',
        'dash-cytoscape',
        'plotly',
    ],
)