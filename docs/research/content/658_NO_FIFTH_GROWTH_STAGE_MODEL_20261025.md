# 658 미지의 5단계 아즈론: 클라이언트에 모델이 없다

Date: 2026-10-25

나무위키 퍼니또 문서와 `_web_azrok_lore.md` §진화 5단계의 떡밥("아즈론은 5단계까지 크지만 5단계 모습은 실루엣뿐이고 아무도 본 적 없다")을 원본 설치본 파일로 직접 대조했다.

## 결론

- **VERIFIED (파일 실측):** `Data\Temp_Character` 의 아즈론 모델은 종족마다 알 모델 하나와 1~4번뿐이다.
  `Abo_Egg/Abo1/Abo2/abo3/Abo4`, `Ark_Egg/Ark1~4`, `Paz_Egg/Paz1~4`, `Tero_Egg/Tero1~4`.
- **VERIFIED (파일 실측):** `Data\Temp_Character\HeadPet` 은 `HP_{Abo,Ark,Paz,Tero}{1..4}.mdl` 뿐이다(`HP_Ark2.bak` 별도).
- **VERIFIED (파일 실측):** `Data\Plaza\Model` 의 아즈론 모델은 `P_{AK,AO,PZ,TO}_{2,3,4}.mdl` 뿐이다.
- **VERIFIED (파일 실측):** `Data` 전체에서 종족 코드 뒤 단계 숫자는 1~4만 나온다. 이름에 5가 붙은 파일은 효과음 `se_ex{abo,ark,paz,tero}_5.ogg` 와 텍스처 프레임 번호 `P_*_{G,R,S}_5.pcx`, `P_*_{G,R,S}_15.pcx` 뿐이다.
- **VERIFIED (`Azrok_original.exe` 문자열):** 아즈론 텍스처 경로 형식은 `Data\Texture\%s_G_%s_%d.pcx`, `_S_`, `_R_`, `_B_` 네 가지다. 다섯 번째 색 접두어는 없다.
- **INFERRED:** B/R/S/G 는 content/106 에서 확정한 단계명 블루론(0)·레드론(1)·실버론(2)·골드론(3)의 앞글자다. 모델 1~4번이 이 네 단계, `_Egg` 가 알(화이트론)에 대응한다.
- **INFERRED:** 위키의 "골드론 다음 미지의 5단계"는 이 설치본 기준 클라이언트에 3D 모델 자체가 없다. 뮤리 5단계 일러스트 유출 증언과는 모순되지 않는다(2D 일러스트만 있었을 수 있다).
- **NOT VERIFIED:** 이 설치본의 마지막 갱신 흔적(별마루 `version.dat` 2011-05-01) 이후 패치에서 5단계 모델이 추가됐는지. 게임 코드가 단계값 4 를 받았을 때의 동작.

## 재현

```bash
ls Data/Temp_Character Data/Temp_Character/HeadPet Data/Plaza/Model
find Data -iregex '.*\(abo\|ark\|paz\|tero\|p_ak\|p_ao\|p_pz\|p_to\|hp_\)[^/]*5[^/]*'
strings -n 6 Azrok_original.exe | grep -E 'Data\\Texture\\%s_[GSRB]_'
```

Related: `_web_azrok_lore.md` (진화 5단계 떡밥 원문 요약), content/106 (진화 단계명), content/652 (레드론 이후 성장 조건).
