import os, json, requests
import xmltodict
from dotenv import load_dotenv
load_dotenv()

service_key = os.getenv("SERVICE_KEY")

DtInfo_mapping = {
    'rcvSat': '접수 시간_토요일',
    'emyNgtTelNo1': '야간 응급실 전화번호1',
    'emyNgtTelNo2': '야간 응급실 전화번호2',
    'lunchWeek': '점심시간_평일(월~금)',
    'lunchSat': '점심시간_토요일',
    'rcvWeek': '접수 시간_평일',
    'parkXpnsYn': '주차장 운영 여부 및 주차비용 부담 여부',
    'parkEtc': '기타 안내 사항',
    'noTrmtSun': '일요일 휴진 안내',
    'noTrmtHoli': '공휴일 휴진 안내',
    'emyDayYn': '주간 응급실 운영 여부',
    'emyDayTelNo1': '주간 응급실 전화번호1',
    'emyDayTelNo2': '주간 응급실 전화번호2',
    'emyNgtYn': '야간 응급실 운영 여부',
    'parkQty': '주차 가능 대수'
}

day_mapping = {
    'Mon': '월요일',
    'Tue': '화요일',
    'Wed': '수요일',
    'Thu': '목요일',
    'Fri': '금요일',
    'Sat': '토요일',
    'Sun': '일요일'
}


def getDtInfo(hospCode):
    url = 'https://apis.data.go.kr/B551182/MadmDtlInfoService2.7/getDtlInfo2.7'
    params = {
        'serviceKey': service_key,
        'ykiho': hospCode,
    }
    response = requests.get(url, params=params)
    dict_x = xmltodict.parse(response.content)
    json_x = json.loads(json.dumps(dict_x))

    if (
        'response' in json_x and
        'body' in json_x['response'] and
        'items' in json_x['response']['body'] and
        json_x['response']['body']['items'] is not None
    ):
        items = json_x['response']['body']['items'].get('item', [])
    else:
        return []

    results = {DtInfo_mapping.get(key, key): value for key, value in items.items() if key in DtInfo_mapping}

    for eng_day, kor_day in day_mapping.items():
        start_key = f'trmt{eng_day}Start'
        end_key = f'trmt{eng_day}End'
        if start_key in items and end_key in items:
            results[f'진료 시간_{kor_day}'] = f"{items[start_key]}~{items[end_key]}"

    if 'plcNm' in items and 'plcDir' in items and 'plcDist' in items:
        results['공공건물(장소) 정보'] = f"{items['plcNm']} ({items['plcDir']}, {items['plcDist']})"

    return results

def getSpclDiagInfo(hospCode):
    url = 'https://apis.data.go.kr/B551182/MadmDtlInfoService2.7/getSpclDiagInfo2.7'
    params = {
        'serviceKey': service_key,
        'ykiho': hospCode,
    }
    response = requests.get(url, params=params)
    dict_x = xmltodict.parse(response.content)
    json_x = json.loads(json.dumps(dict_x))

    if (
        'response' in json_x and
        'body' in json_x['response'] and
        'items' in json_x['response']['body'] and
        json_x['response']['body']['items'] is not None
    ):
        items = json_x['response']['body']['items'].get('item', [])
    else:
        return []
    result = [
        {
            'srchCdNm': item['srchCdNm'],
        } for item in items
        ]
    return result

def getTrnsprtInfo(hospCode):
    url = 'https://apis.data.go.kr/B551182/MadmDtlInfoService2.7/getTrnsprtInfo2.7'
    params = {
        'serviceKey': service_key,
        'ykiho': hospCode,
    }
    response = requests.get(url, params=params)
    dict_x = xmltodict.parse(response.content)
    json_x = json.loads(json.dumps(dict_x))

    if (
        'response' in json_x and
        'body' in json_x['response'] and
        'items' in json_x['response']['body'] and
        json_x['response']['body']['items'] is not None
    ):
        items = json_x['response']['body']['items'].get('item', [])
    else:
        return []

    result = [
        f"{item.get('lineNo', '정보 없음')} {item.get('trafNm', '정보 없음')} {item.get('arivPlc', '정보 없음')}에서 {item.get('dir', '정보 없음')} 병원까지의 거리: {item.get('dist', '정보 없음')}"
        for item in items if isinstance(item, dict)
    ]
    
    return result

def getHospBasisList(longtitude, latitude, dgsbjtCd, radius=30000):
    url = 'http://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList'
    params = {
        'serviceKey': service_key,
        'pageNo': 1,
        'numOfRows': 10,
        'zipCd': '', # 분류코드
        'clCd': '', # 종별코드
        'dgsbjtCd': dgsbjtCd,
        'xPos': longtitude,
        'yPos': latitude,
        'radius': radius
    }
    response = requests.get(url, params=params)
    dict_x = xmltodict.parse(response.content)
    json_x = json.loads(json.dumps(dict_x))

    if (
        'response' in json_x and
        'body' in json_x['response'] and
        'items' in json_x['response']['body'] and
        json_x['response']['body']['items'] is not None
    ):
        items = json_x['response']['body']['items'].get('item', [])
    else:
        return []
    
    result = sorted(
        [
            {
                '이름': item['yadmNm'],
                '주소': item['addr'],
                '유형명': item['clCdNm'],
                '전화번호': item['telno'],
                '거리': round(float(item['distance'])),
                '전체의사수': int(item['drTotCnt']),
                'XPos': item['XPos'],
                'YPos': item['YPos'],
                '병원코드': item['ykiho']
            }
            for item in items
        ],
        key=lambda x: x['거리']
    )

    for hospital in result:
        hosp_code = hospital.pop('병원코드', None)

        # 상세 정보
        detail_info = getDtInfo(hosp_code)
        hospital.update(detail_info)

        # 특수진단 정보
        special_diag_info = getSpclDiagInfo(hosp_code)
        hospital['특수진단정보'] = [info['srchCdNm'] for info in special_diag_info]

        # 교통
        trnsprt_info = getTrnsprtInfo(hosp_code)
        hospital['교통정보'] = trnsprt_info
        
    return json.dumps({
        "status": "00",
        "message": "NORMAL_SERVICE",
        "data": result
    }, ensure_ascii=False, indent=4)