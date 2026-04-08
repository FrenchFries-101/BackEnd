from sqlalchemy.orm import Session
from recommendation.changsha_models import CityWeather, CitySights


def seed_city_data(db: Session) -> None:
    """初始化城市信息种子数据"""
    # 检查天气数据是否已存在
    weather_count = db.query(CityWeather).count()
    if weather_count == 0:
        # 初始化天气数据
        weather_data = [
            CityWeather(
                month=3,
                description="Rainy season, watch out riding e-scooters!",
                icon="static/icons/rain.gif"
            ),
            CityWeather(
                month=4,
                description="Rainy but warming up, enjoy spring flowers!",
                icon="static/icons/rain.gif"
            ),
            CityWeather(
                month=5,
                description="Sunny and warm, perfect for outdoor activities!",
                icon="static/icons/sunny.gif"
            ),
        ]
        db.add_all(weather_data)
        print("✅ 天气数据初始化完成")
    else:
        print(f"ℹ️  天气数据已存在，跳过初始化（{weather_count} 条）")
    
    # 检查景点数据是否已存在
    sights_count = db.query(CitySights).count()
    if sights_count == 0:
        # 初始化景点数据
        sights_data = [
            CitySights(
                title="Hunan Botanical Garden",
                description="Enjoy flowers and beautiful garden scenery",
                icon="static/icons/flower.gif",
                image="static/images/hunan_garden.png",
                address="Kaifu District, Changsha, Hunan",
                copyright="https://baike.baidu.com/item/%E6%B9%96%E5%8D%97%E7%9C%81%E6%A3%AE%E6%9E%97%E6%A4%8D%E7%89%A9%E5%9B%AD/6068095"
            ),
            CitySights(
                title="Yuelu Mountain",
                description="Hiking, lake view, historical culture",
                icon="static/icons/mountain.gif",
                image="static/images/yuelu_mountain.png",
                address="Yuelu District, Changsha, Hunan",
                copyright="https://ibaotu.com/sucai/19434921.html"
            ),
            CitySights(
                title="Orange Isle",
                description="Walking, sightseeing, night fireworks show",
                icon="static/icons/island.gif",
                image="static/images/juzizhou.png",
                address="Xiangjiang River, Changsha, Hunan",
                copyright="https://haowallpaper.com/homeViewLook/17690785630768512"
            ),
        ]
        db.add_all(sights_data)
        print("✅ 景点数据初始化完成")
    else:
        print(f"ℹ️  景点数据已存在，跳过初始化（{sights_count} 条）")
    
    db.commit()
