# 2011.img — 추출 + 원본 설치본 대조

설치본(`Azrok_Plaza`, `starmaru`)은 이미 프로젝트에 있으므로 **복사하지 않고 대조만** 했다.

## 1. 설치본 대조 결과

- 크기 일치: **4568개**
- 우리 사본에 **없는** 파일: **48개**
- 크기가 **다른** 파일: **1개**

### 우리에게 없는 원본 파일

| 2011 원본 경로 | 크기 |
|---|---:|
| `Program Files\Hansol\Azrok_Plaza\Data\Common\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Error\Thumbs.db` | 13824 |
| `Program Files\Hansol\Azrok_Plaza\Data\Game\Thumbs.db` | 8704 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\Calendar\Thumbs.db` | 5632 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\CharacterInfo\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\Clean\Thumbs.db` | 5632 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\Condition\Thumbs.db` | 5120 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\Equip\Thumbs.db` | 7680 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\Exp\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\MainMenu\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\MyBag\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\Option\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\Quest\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\StateList\Thumbs.db` | 8192 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\State\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Interface\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Lobby\SelectEgg\Thumbs.db` | 12288 |
| `Program Files\Hansol\Azrok_Plaza\Data\Lobby\SelectPet\Thumbs.db` | 8704 |
| `Program Files\Hansol\Azrok_Plaza\Data\Lobby\Thumbs.db` | 27136 |
| `Program Files\Hansol\Azrok_Plaza\Data\NPC\Model\Thumbs.db` | 5632 |
| `Program Files\Hansol\Azrok_Plaza\Data\NPC\Thumbs.db` | 8192 |
| `Program Files\Hansol\Azrok_Plaza\Data\OutMap\ArimCook\Thumbs.db` | 9728 |
| `Program Files\Hansol\Azrok_Plaza\Data\OutMap\Bingbing\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\OutMap\Magic\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\OutMap\MuryPlay\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\OutMap\PaziKnow\Thumbs.db` | 8704 |
| `Program Files\Hansol\Azrok_Plaza\Data\OutMap\Result\Thumbs.db` | 8704 |
| `Program Files\Hansol\Azrok_Plaza\Data\OutMap\TeroGym\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\OutMap\Thumbs.db` | 10752 |
| `Program Files\Hansol\Azrok_Plaza\Data\Paticle\Thumbs.db` | 7680 |
| `Program Files\Hansol\Azrok_Plaza\Data\SelectEgg\Thumbs.db` | 7680 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\ArimCook\Thumbs.db` | 8192 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\ItemShop\Thumbs.db` | 8192 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\Magic\Thumbs.db` | 7680 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\MuryPlay\Thumbs.db` | 8192 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\OXquiz\Thumbs.db` | 18432 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\Pazi\Thumbs.db` | 5632 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\Plaza\Thumbs.db` | 398848 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\PopcornGame\Thumbs.db` | 5120 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\PopcornGame\popcorn_CBT3\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\SelectPet\Thumbs.db` | 5632 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\TeroGym\Thumbs.db` | 7168 |
| `Program Files\Hansol\Azrok_Plaza\Data\Space\lobby\Thumbs.db` | 5632 |
| `Program Files\Hansol\Azrok_Plaza\Data\Texture\Thumbs.db` | 362496 |
| `Program Files\Hansol\Azrok_Plaza\Data\Thumbs.db` | 12288 |
| `Program Files\Hansol\Azrok_Plaza\Data\button\Thumbs.db` | 9216 |
| `Program Files\Hansol\Azrok_Plaza\Thumbs.db` | 9216 |
| `Program Files\Hansol\Azrok_Plaza\azrok.lg` | 23 |

### 크기가 다른 파일 (패치 레벨 차이 가능)

| 경로 | 2011 원본 | 우리 사본 |
|---|---:|---:|
| `Program Files\Hansol\Azrok_Plaza\Azrok.txt` | 994 | 129651 |

## 2. 새로 추출한 파일 (152개)

위치: `<home>\Documents\<project-dir>\Azrok_Plaza\docs\research\_img2011_extracted`

`DEL` = 삭제됐던 레코드에서 복구.

| 원본 경로 | 크기 | DEL |
|---|---:|---|
| `<broken_reference_0x8659#3>\skin_funittomania_left_top[1].gif` | 6086 | DEL |
| `<broken_reference_0xaaa7#6>\skin_funittomania_left_bg[1].gif` | 104 | DEL |
| `<broken_reference_0xaaa7#6>\skin_funittomania_left_bottom[1].gif` | 4997 | DEL |
| `<broken_reference_0xaaa7#6>\starmaru[1].css` | 2604 | DEL |
| `<broken_reference_0xaaa7#6>\starmaru_progressbar[1].htm` | 3055 | DEL |
| `<broken_reference_0xc31a#3>\skin_funittomania_menu[1].gif` | 8765 | DEL |
| `<broken_reference_0xc31f#2>\login_funitto_do[1].htm` | 137 | DEL |
| `<broken_reference_0xfa1d#1>\funitto_jaeminara_co_kr[1].htm` | 155 | DEL |
| `<broken_reference_0xfa1f#1>\skin_funittomania_body[1].jpg` | 9366 | DEL |
| `<broken_reference_0xfa1f#1>\skin_funittomania_top[1].jpg` | 640098 | DEL |
| `Documents and Settings\Guest\Local Settings\Temporary Internet Files\Content.IE5\IH38666J\funitto_icon_01[1].gif` | 3466 |  |
| `Documents and Settings\Guest\Local Settings\Temporary Internet Files\Content.IE5\IH38666J\funitto_icon_02[1].gif` | 3106 |  |
| `Documents and Settings\Guest\Local Settings\Temporary Internet Files\Content.IE5\IH38666J\funitto_icon_03[1].gif` | 3333 |  |
| (개인 PC 사용 흔적 목록은 공개본에서 뺐다) | | |
| `WINDOWS\Downloaded Program Files\AzrokStarter.inf` | 551 |  |
| `WINDOWS\Downloaded Program Files\AzrokStarter.ocx` | 36864 |  |
| `WINDOWS\Prefetch\STARMARU.EXE-16A5D751.pf` | 59650 | DEL |
| `WINDOWS\system32\AzrokInstaller.exe` | 684120 |  |
| `hansol\HansolFunnyMini\Angel.dll` | 65536 |  |
| `hansol\HansolFunnyMini\Angel.gp3` | 1565024 |  |
| `hansol\HansolFunnyMini\Arithmetic.dll` | 65536 |  |
| `hansol\HansolFunnyMini\Arithmetic.gp3` | 1583017 |  |
| `hansol\HansolFunnyMini\BabyBoom.dll` | 81920 |  |
| `hansol\HansolFunnyMini\BabyBoom.gp3` | 2788536 |  |
| `hansol\HansolFunnyMini\Barbell.dll` | 61440 |  |
| `hansol\HansolFunnyMini\Barbell.gp3` | 2375148 |  |
| `hansol\HansolFunnyMini\BigNumber.dll` | 61440 |  |
| `hansol\HansolFunnyMini\BigNumber.gp3` | 1311275 |  |
| `hansol\HansolFunnyMini\BirdDung.dll` | 77824 |  |
| `hansol\HansolFunnyMini\BirdDung.gp3` | 1785383 |  |
| `hansol\HansolFunnyMini\Bump.dll` | 69632 |  |
| `hansol\HansolFunnyMini\Bump.gp3` | 3645320 |  |
| `hansol\HansolFunnyMini\CardSet.dll` | 73728 |  |
| `hansol\HansolFunnyMini\CardSet.gp3` | 1621297 |  |
| `hansol\HansolFunnyMini\CatDream.dll` | 65536 |  |
| `hansol\HansolFunnyMini\CatDream.gp3` | 1379806 |  |
| `hansol\HansolFunnyMini\CatchFlies.dll` | 61440 |  |
| `hansol\HansolFunnyMini\CatchFlies.gp3` | 1252322 |  |
| `hansol\HansolFunnyMini\ChocoBall.dll` | 69632 |  |
| `hansol\HansolFunnyMini\ChocoBall.gp3` | 1507388 |  |
| `hansol\HansolFunnyMini\Chrun.dll` | 65536 |  |
| `hansol\HansolFunnyMini\Chrun.gp3` | 1375660 |  |
| `hansol\HansolFunnyMini\CryPtograph.dll` | 61440 |  |
| `hansol\HansolFunnyMini\CryPtograph.gp3` | 1082604 |  |
| `hansol\HansolFunnyMini\Cursor.ani` | 21566 |  |
| `hansol\HansolFunnyMini\Fishing.dll` | 77824 |  |
| `hansol\HansolFunnyMini\Fishing.gp3` | 1383343 |  |
| `hansol\HansolFunnyMini\GatherStar.dll` | 69632 |  |
| `hansol\HansolFunnyMini\GatherStar.gp3` | 948940 |  |
| `hansol\HansolFunnyMini\HHBroken.dll` | 65536 |  |
| `hansol\HansolFunnyMini\HHBroken.gp3` | 2175278 |  |
| `hansol\HansolFunnyMini\Haby.dll` | 81920 |  |
| `hansol\HansolFunnyMini\Haby.gp3` | 1636299 |  |
| `hansol\HansolFunnyMini\Hammer.dll` | 69632 |  |
| `hansol\HansolFunnyMini\Hammer.gp3` | 2626886 |  |
| `hansol\HansolFunnyMini\Hanja1.dll` | 90112 |  |
| `hansol\HansolFunnyMini\Hanja1.gp3` | 882462 |  |
| `hansol\HansolFunnyMini\Hanja2.dll` | 98304 |  |
| `hansol\HansolFunnyMini\Hanja2.gp3` | 1122827 |  |
| `hansol\HansolFunnyMini\HansolGameKing.exe` | 520192 |  |
| `hansol\HansolFunnyMini\Help.ogg` | 57818 |  |
| `hansol\HansolFunnyMini\Install.bin` | 6043 |  |
| `hansol\HansolFunnyMini\JumpBoy.dll` | 65536 |  |
| `hansol\HansolFunnyMini\JumpBoy.gp3` | 1644370 |  |
| `hansol\HansolFunnyMini\KBService.gp3` | 1246125 |  |
| `hansol\HansolFunnyMini\KbService.dll` | 77824 |  |
| `hansol\HansolFunnyMini\KillUfo.dll` | 61440 |  |
| `hansol\HansolFunnyMini\KillUfo.gp3` | 1885813 |  |
| `hansol\HansolFunnyMini\LastShot.dll` | 65536 |  |
| `hansol\HansolFunnyMini\LastShot.gp3` | 2033558 |  |
| `hansol\HansolFunnyMini\Log.txt` | 115 |  |
| `hansol\HansolFunnyMini\Microsoft.VC80.CRT.manifest` | 522 |  |
| `hansol\HansolFunnyMini\MilkMania.dll` | 65536 |  |
| `hansol\HansolFunnyMini\MilkMania.gp3` | 1783283 |  |
| `hansol\HansolFunnyMini\MissNum.dll` | 69632 |  |
| `hansol\HansolFunnyMini\MissNum.gp3` | 1385609 |  |
| `hansol\HansolFunnyMini\MonkeyWookey.dll` | 65536 |  |
| `hansol\HansolFunnyMini\MonkeyWookey.gp3` | 3023241 |  |
| `hansol\HansolFunnyMini\Mosquito.dll` | 65536 |  |
| `hansol\HansolFunnyMini\Mosquito.gp3` | 4277205 |  |
| `hansol\HansolFunnyMini\MusicGirl.dll` | 65536 |  |
| `hansol\HansolFunnyMini\MusicGirl.gp3` | 3057151 |  |
| `hansol\HansolFunnyMini\Option.dat` | 7 |  |
| `hansol\HansolFunnyMini\PerpectShot.dll` | 77824 |  |
| `hansol\HansolFunnyMini\PerpectShot.gp3` | 1950253 |  |
| `hansol\HansolFunnyMini\Pigy.dll` | 61440 |  |
| `hansol\HansolFunnyMini\Pigy.gp3` | 1523636 |  |
| `hansol\HansolFunnyMini\RedAlret.dll` | 69632 |  |
| `hansol\HansolFunnyMini\RedAlret.gp3` | 1224994 |  |
| `hansol\HansolFunnyMini\RunAway.gp3` | 2166666 |  |
| `hansol\HansolFunnyMini\ScooterSlide.gp3` | 2007864 |  |
| `hansol\HansolFunnyMini\Screenshot\GK02d110208204158.jpg` | 133431 |  |
| `hansol\HansolFunnyMini\Screenshot\GK02d110224200055.jpg` | 192656 |  |
| `hansol\HansolFunnyMini\Screenshot\GK02d110224200854.jpg` | 187594 |  |
| `hansol\HansolFunnyMini\SelectCard.dll` | 65536 |  |
| `hansol\HansolFunnyMini\SelectCard.gp3` | 1303980 |  |
| `hansol\HansolFunnyMini\Server.dat` | 30 |  |
| `hansol\HansolFunnyMini\SkiSchool.dll` | 77824 |  |
| `hansol\HansolFunnyMini\SkiSchool.gp3` | 1794998 |  |
| `hansol\HansolFunnyMini\SlanderList.dat` | 4756 |  |
| `hansol\HansolFunnyMini\Sprinter.dll` | 65536 |  |
| `hansol\HansolFunnyMini\Sprinter.gp3` | 820060 |  |
| `hansol\HansolFunnyMini\Track.dat` | 45 |  |
| `hansol\HansolFunnyMini\Vampire.dll` | 69632 |  |
| `hansol\HansolFunnyMini\Vampire.gp3` | 1578040 |  |
| `hansol\HansolFunnyMini\bgm_training.ogg` | 368972 |  |
| `hansol\HansolFunnyMini\bgm_type01.ogg` | 340278 |  |
| `hansol\HansolFunnyMini\bgm_type02.ogg` | 278953 |  |
| `hansol\HansolFunnyMini\bgm_type03.ogg` | 390955 |  |
| `hansol\HansolFunnyMini\bgm_type04.ogg` | 460876 |  |
| `hansol\HansolFunnyMini\bgm_type05.ogg` | 234290 |  |
| `hansol\HansolFunnyMini\bgm_type06.ogg` | 345629 |  |
| `hansol\HansolFunnyMini\bgm_type07.ogg` | 368972 |  |
| `hansol\HansolFunnyMini\bgm_type08.ogg` | 280413 |  |
| `hansol\HansolFunnyMini\bgm_type09.ogg` | 498923 |  |
| `hansol\HansolFunnyMini\bgm_type10.ogg` | 553784 |  |
| `hansol\HansolFunnyMini\bgm_type11.ogg` | 234290 |  |
| `hansol\HansolFunnyMini\bgm_type12.ogg` | 368972 |  |
| `hansol\HansolFunnyMini\bgm_type13.ogg` | 460876 |  |
| `hansol\HansolFunnyMini\bgm_ui_01.ogg` | 477809 |  |
| `hansol\HansolFunnyMini\bgm_ui_02.ogg` | 623747 |  |
| `hansol\HansolFunnyMini\bgm_ui_03.ogg` | 661851 |  |
| `hansol\HansolFunnyMini\bgm_ui_04.ogg` | 497860 |  |
| `hansol\HansolFunnyMini\bgm_ui_05.ogg` | 309451 |  |
| `hansol\HansolFunnyMini\bgm_ui_06.ogg` | 477809 |  |
| `hansol\HansolFunnyMini\bgm_ui_07.ogg` | 203525 |  |
| `hansol\HansolFunnyMini\bgm_ui_08.ogg` | 398019 |  |
| `hansol\HansolFunnyMini\bgm_ui_chr_shop.ogg` | 648529 |  |
| `hansol\HansolFunnyMini\bgm_ui_intro.ogg` | 155337 |  |
| `hansol\HansolFunnyMini\bgm_ui_item_shop.ogg` | 460809 |  |
| `hansol\HansolFunnyMini\bgm_ui_lobby.ogg` | 300720 |  |
| `hansol\HansolFunnyMini\bgm_ui_main.ogg` | 750703 |  |
| `hansol\HansolFunnyMini\bgm_ui_myroom.ogg` | 484851 |  |
| `hansol\HansolFunnyMini\bgm_ui_ready.ogg` | 239502 |  |
| `hansol\HansolFunnyMini\bgm_ui_result1.ogg` | 122178 |  |
| `hansol\HansolFunnyMini\bgm_ui_result2.ogg` | 153165 |  |
| `hansol\HansolFunnyMini\bgm_ui_select.ogg` | 238100 |  |
| `hansol\HansolFunnyMini\d3dx9_27.dll` | 2319568 |  |
| `hansol\HansolFunnyMini\msvcm80.dll` | 479232 |  |
| `hansol\HansolFunnyMini\msvcp80.dll` | 548864 |  |
| `hansol\HansolFunnyMini\msvcr80.dll` | 626688 |  |
| `hansol\HansolFunnyMini\ogg.dll` | 13312 |  |
| `hansol\HansolFunnyMini\unicows.dll` | 245408 |  |
| `hansol\HansolFunnyMini\vorbis.dll` | 991232 |  |
| `hansol\HansolFunnyMini\vorbisfile.dll` | 19968 |  |

(크기 초과로 건너뜀: 4개)
