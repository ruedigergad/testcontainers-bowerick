import setuptools

setuptools.setup(
    name='testcontainers-bowerick',
    packages=setuptools.find_packages(exclude=['tests']),
    version='0.1.0',
    description='Support multiple Message-oriented Middleware (MoM) protocols (MQTT, STOMP, STOMP via WebSockets, OpenWire) via testcontainers.',
    author='Ruediger Gad',
    author_email='r.c.g@gmx.de',
    url='https://github.com/ruedigergad/testcontainers-bowerick',
    keywords=['testing', 'message-oriented middleware', 'docker', 'test automation', 'mqtt', 'stomp', 'websockets', 'openwire'],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Operating System :: POSIX',
    ],
    install_requires=[
        'stomp.py',
        'testcontainers'
    ],
    python_requires='>=3.6',
)
