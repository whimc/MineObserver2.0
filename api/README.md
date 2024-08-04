# Running ML-API

## Terminal Steps
<hr/>

```
conda create -n {YOUR_ENV_NAME} python3.8
conda activate {YOUR_ENV_NAME}
bash install.sh
python main.py
```

This will create a flask API that runs the ML solution. For our purposes, we hosted this on an AWS EC2 instance. If you want to run this without shutting down the terminal:

```
nohup python3 main.py &
```





## How to access ##
<hr/>

To access: *endpoint*/*TASK*





## Commands ##
| **TASK**      	| **REQUEST** 	| **REQUIRED INFO**                        	| **OPTIONAL INFO** 	| **RETURNS**                                                   	|
|---------------	|-------------	|------------------------------------------	|-------------------	|---------------------------------------------------------------	|
| caption-image 	| POST        	| image: bytes<br><br>user-caption: string<br><br> 	| user: string      	| feedback: string<br>score: float<br>generated caption: string 	|
|               	|             	|                                          	|                   	|                                                               	|


