"""天气数据更新 Worker"""
import requests
from .base import BaseWorker


class WeatherWorker(BaseWorker):
    """天气数据更新线程"""
    
    def __init__(self, data_store, interval, config=None, logger=None):
        super().__init__(data_store, interval, logger)
        self.config = config
        
        # 从配置读取参数
        if config:
            self.api_key = config.get("weather.api_key", "")
            self.city_id = config.get("weather.city_id", "")
        else:
            self.api_key = ""
            self.city_id = ""
    
    def update(self) -> None:
        """更新天气数据"""
        if not self.api_key or not self.city_id:
            self._log('warning', "Weather API key or city ID not configured")
            return
        
        try:
            base_url = "https://devapi.qweather.com/v7"
            urls = {
                "now": f"{base_url}/weather/now?location={self.city_id}&key={self.api_key}",
                "forecast": f"{base_url}/weather/3d?location={self.city_id}&key={self.api_key}",
                "air": f"{base_url}/air/now?location={self.city_id}&key={self.api_key}",
                "life": f"{base_url}/indices/1d?type=3&location={self.city_id}&key={self.api_key}"
            }
            
            responses = {}
            for key, url in urls.items():
                try:
                    resp = requests.get(url, timeout=10)
                    resp.raise_for_status()
                    responses[key] = resp.json()
                except requests.RequestException as e:
                    self._log('warning', f"天气API请求失败 {key}: {e}")
                    responses[key] = {}
            
            # 更新当前天气
            if responses.get("now", {}).get("code") == "200":
                now_data = responses["now"]["now"]
                self.data_store.update({
                    "temp": now_data.get("temp", "--"),
                    "text": now_data.get("text", "..."),
                    "feelsLike": now_data.get("feelsLike", "--"),
                    "humidity": now_data.get("humidity", "--"),
                    "windSpeed": now_data.get("windSpeed", "--"),
                    "windDir": now_data.get("windDir", "--")
                })
            
            # 更新预报
            if responses.get("forecast", {}).get("code") == "200":
                forecast_data = responses["forecast"].get("daily", [])
                self.data_store.set("forecast", forecast_data)
                # 保存今天的预报数据
                if forecast_data:
                    self.data_store.set("today", forecast_data[0])
            
            # 更新空气质量
            if responses.get("air", {}).get("code") == "200":
                self.data_store.set("aqi", responses["air"]["now"].get("aqi", "0"))
            
            # 更新生活指数
            if responses.get("life", {}).get("code") == "200":
                life_data = responses["life"].get("daily", [])
                if life_data:
                    self.data_store.set("life", life_data[0].get("category", ""))
            
            self._log('debug', "天气数据更新成功")
            
        except Exception as e:
            self._log('error', f"天气更新线程异常: {e}")
