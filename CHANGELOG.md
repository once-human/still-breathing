# Changelog

Versions follow [SemVer](https://semver.org), counted by what a buyer would notice. Changes go live with every push and are noted under Unreleased; a release is cut when a set of them is finished (`npm run release`), and the bump follows from the sections:
- **Lineup** → MAJOR: a new drop or lineup, or the shop working differently (checkout, prices, a redesign).
- **New / Changed** → MINOR: a new shirt, colour or feature; new art or lettering on a shirt; a rename.
- **Fixed** → PATCH: fixes and polish: copy, a render refresh, a layout bug.

The shop stays 0.x until launch, which is 1.0.0. Every release is a git tag `vX.Y.Z` and a GitHub release with the studio renders that changed attached.

## Unreleased
### Lineup
- The shop says plainly what it is: lineup 01 is fred again.. india now, everywhere, and its address is /fred-again-india (each shirt at /fred-again-india/crowd and the rest); the old /lineup-01 links still work and land there. /lineups is now /shop, every shirt by city with its price.
- Each shirt's page is the shirt and buying it: the 3D, then its name, its price big, a short word on what's on both sides, the colour, the size, the buy button and right under it when it usually arrives (dates worked out from today), that delivery is free, what happens if something's wrong, and the size guide. Cloth and care fold away under it. The sections that ran on below (front and back again, worn at the show, sizes, more shirts) are gone, and the page always opens at its top. On a phone, once the buy button scrolls away, a slim bar with the shirt, its size, its price and the button stays at the bottom.
- In the 3D the views go the tee, on the table, then worn; worn is the only place a person appears on the site, and the him / her switch shows only there.
- Point at any shirt and its print shows on the shirt's own colour, the whole print area at true size so a chest mark looks as small as it is: the front for about two seconds, slowly closer, then the back, and round again. No people in the cards, the home page or share pictures.
- One quiet line over every page: free delivery anywhere in india, made to order, with you in about 10 days. The home and shop pages have four plain facts: the price with all taxes included, free delivery, made to order, heavy cotton.
- Your order has its own page, linked from every order email, or found at /order with its number and your email: in, being made, on its way, with you, with the courier and tracking link once it leaves.
- Buying: every shirt has add to bag and buy now right by its price, ₹1,270 with all taxes and shipping included, nothing added at the end; the header always shows the bag. The bag opens at the side, where you change how many or take one out; buy now goes straight to checkout, which asks where it goes, and you pay by UPI (first), card or net banking in Razorpay's secure window. Paid, the order goes to print by itself after an hour, a confirmation email comes at once, and the tracking by email when it leaves. Until payment is connected, the bag and checkout still work but checkout says plainly that nothing can be paid or ordered yet.
- Accounts and orders: sign in at /account with your email and a 6-digit code we send (no password). Your account keeps your name, phone and up to five addresses, so checkout fills itself in, and lists every order placed with your email: where each is, tracking, its receipt, and order these again. Each order's page now shows everything that has happened to it with the time (placed, paid and how, sent to print, each update from the workshop, left with the courier and the tracking number, out for delivery, delivered), the payment and any refund with their references, and a receipt to print or save as PDF (a receipt, not a GST tax invoice). For the first hour after paying an order waits before going to print: on its page, with the time it closes, you can cancel it yourself and be refunded in full straight away, or fix the address. After that, cancelling is by writing in, as before.
- The site is a store with real pages now, and a new layout of its own. A home page for the label with lineup 01 up front and its five shirts; a lineups page; lineup 01's own page (fred again.. india, fan made) with the five nights, the shirts by city and their story; and a page for each shirt at its own address (/lineup-01/crowd, /lineup-01/map-mumbai and the rest) with the 3D, him or her, fit, try-on and the lights, its front and back side by side, worn at the show, cloth, care and sizes. Going from one shirt to the next keeps the 3D up and only swaps the shirt. A size guide, a help page and a proper not-found page. The header has real links, opens the five shirts over lineup 01 and gets out of the way as you read; on a phone it's a full-screen menu. Every page ends in the same footer. Each page has its own title, description and share picture made from the studio renders, and the site has a sitemap. The home and lineup pages show the renders only, so they open fast; the 3D loads on a shirt's page.
### New
- Admin people and accounts: people is everyone the shop knows by email, accounts and guest buyers together (everyone, bought, came back, has an account, guests, never paid), and each person's page has what they spent, their orders, contact, saved addresses, how many devices they're signed in on, what you can do and your notes. Accounts lists every account made at /account: signed in now, ordered, never ordered. The old customers address goes to people.
- Admin money page: for this month, 30 days, 7 days or all time, what you keep, sales, shirts sold and an average order against the time before; where the money went line by line (refunds, Qikink, payment fees, post); what Razorpay still holds and its last payout; each shirt sold by size; and every month since the first order.
- The admin knows who's here: live now (everyone on the site this minute, the page they're on, where they came from, what's in their bag, every 5 seconds), visitors (every visit page by page with time on screen and how far down, filters by source, city, shirt and how far they got, people who come back, and the bots and link previews kept apart), and activity (each shirt step by step from seen to paid, pages, sources, places, devices, screens and languages). Kept 90 days, then daily totals; no IP addresses, never tied to a name or an order.
- The privacy page shows each visitor everything kept about their browser, with a switch to turn counting off and a button to delete it all at once. The policy says what's kept and for how long.
- Admin home: live count, today against yesterday, the "taking orders" switch and each shirt's status right there, latest orders with cancelled and refunded marked, latest visitors. A "what's live" page asks every service just now (payments, the webhook, Qikink, the order store, email, the sync job) and shows which shirt and size can be bought.
- Orders: change the address, delete a test order. Customers: edit name and phone, sign them out everywhere, delete. Site words from settings: the top line over every page, and what checkout says while orders are off.
- More emails, in the same short style: when an order goes to print, when it's out for delivery, when its address changes, and a note to the shop for every new order. Sign-in emails say which device, browser and city asked; the admin gets an email for every sign-in.
- A health check at /api/shop/health says whether payments are live and whether the print partner accepts the shop's keys (yes or no, never a key).
- Print files for the print partner: every placement of the five shirts on sale as a 300 dpi PNG, transparent where there's no ink, sRGB (pipeline/printfiles.py; the backs are heavy, so printfiles.yml makes them on the farm). All of them are the same masters the site's 3D is made from, so nothing printed differs from the page: the backs at 13.5 x 18 in, the fronts at their printed size with their hard edges cut again at 300 dpi, the wristband turned from its unturned art instead of the jagged turned copy, and the again.. lettering's edges no longer outlined in blue dots.
- An admin for the shop at /admin, for sahn only (a one-time link to the admin's email, no password; 12-hour sessions; every page and action checked on the server and logged). Overview: orders, revenue and the margin after Qikink, Razorpay and post, today, this week and all time; shirts by size; what needs a look. Orders: search and filters, CSV, each order's buyer, address, items, payment and fee, settlement, refunds, Qikink id, status and tracking, the emails sent and a full timeline, with send to print, cancel, refund (any part), resend an email, ask Qikink, and notes, each with a confirm step. Customers with their orders and lifetime spend. Products: status (on sale, sold out, draft), Qikink cost, margin or a fixed price, and the Qikink SKU per size. Activity: visits, pages, sources, devices, bag and checkout per day, counted on the site itself with no cookies and no outside trackers. Settings: taking orders on or off, the margin, the margin maths, and which keys are set. An audit log of everything done there.
- The policies are up: shipping, returns and refunds, terms, privacy and contact, at /policies, from the footer and help. Write to contact@sahn.in.
- Policy pages at /policies/shipping, refunds, terms, privacy and contact, each with the others beside it; the footer and help link to them, and help gets a contact part, as soon as the shop's contact details are filled in. Once the shop is open, help and the footer link to find your order.
- Every shirt in a grid shows its price, and each shirt page and help say how long it takes: made in 2 to 5 days, then 2 to 7 days to you, anywhere in India.
- 05 actual life, a black tee for Bengaluru: the walk home at 1:42 am in light rain, under the rain trees, the street shining wet, the last train in at Madavara and the stage still lit at the end of the road. On the back, notes in hand and bengaluru . 1:42 am . 22°c along the bottom; on the front, the festival wristband hanging from the left chest, clasp up, again.. again.. again.. woven down it
- i am a party has its own front: a small hand-drawn seal on the left chest, in the same place and at the same size as again.. on the other shirts, with again.. फिर से.. पुन्हा.. ಮತ್ತೆ.. between two uneven rings and a warm body seen through a heat camera in the middle, painted in violet, orange and pale yellow round a cream core.
- The maps have their own fronts: each city's map key on the left chest, in the same place and at the same size as again.. on the crowd. Mumbai's reads fred again.., mumbai, 8 + 9 dec over the city, the course, the sea, us, no moon and the sound. Bengaluru's has again.. as its title, with a line running up from each of its two dots to sat 12 and sun 13.
- Worn by him or her: under the 3D view, pick who wears the tee. Two new people, both Indian, lean and athletic: him at 175 cm in M, with a textured quiff, faded sides and a short beard drawn hair by hair; her at 163 cm in S, with an open bob parted in the middle and a soft, natural hairline. Both breathe and shift their weight as they stand, and the tee is simulated on each of their own bodies.
- On the table: the tee laid flat on a worn wooden table, lit by a window on the right whose frame throws a soft shadow across the boards. Air comes in through it, never quite straight: it dies away, breezes, builds slowly or bursts. Now and then a dry leaf (rarely a thread or a hair) drifts down or skates in; it has weight, holding until a puff beats its grip, then breaking loose, skidding and stopping again. Leaves glow a little with the light behind them. The cotton breathes with the air.

### Changed
- Admin orders are one list with views along the top (needs you, in the hour, being made, on the way, delivered, cancelled, not paid) each with its count, one search box and the rest of the filters folded away. An order's page shows where it is as steps, what's wrong first if anything is, then the shirts, the money and what you keep, the timeline, the buyer, and everything you can do to it as one list.
- The admin overview counts by the month, not the day: this month (against the same days last month), 30 days, 7 days or all time, remembered for next time. It opens with what happened since you last looked, then anything that needs you, then people, orders, sales and what you keep, the way from coming in to paying with where people stopped, and each day's visitors with the days an order came marked.
- Admin pages open at once with their outline while the numbers load, and the overview no longer waits on Razorpay and Qikink (the health page still asks them each time).
- The admin's left side is sorted into sections, each with its own few pages: overview; sales (orders, money); customers (people, accounts); shop (shirts, prices, site words); visitors (live now, visits, insights); system (health, settings, audit log). On a phone the main four sit along the bottom and the rest under more.
- The admin is quieter and quicker: cream on black with grey icons, colour only as a small dot for live, needs you or broken, links in the text's own colour, and every switch flips the moment it's tapped while it saves behind (closing the shop still asks first). Motion is a tenth of a second with a light snap.
- Admin home is one calm screen: what needs you (only when something does, each with what to do), four big numbers for today against yesterday (sales, orders, people, margin), the last 30 days as a chart, the latest orders, who's on the site now, and the week and all-time money.
- The admin has six places: home, orders, people, shirts, visitors and settings, down the left, or along the bottom on a phone like an app. The shop's live / closed switch sits at the top right of every page, one tap and a pop-up to be sure.
- The admin's own look, matched to the shop: solid rounded cards, rows with plain line icons, bigger type (15 px to read, nothing under 13), big bold numbers, switches, pop-ups, toasts and the save bar that move with a little spring, pop-ups as sheets from the bottom on a phone. No emojis anywhere; fixed values are simply greyed.
- The admin is easier to work: switches and choices save the moment they change, forms gather changes in a save bar with discard, anything that moves prices or closes checkout asks first, and deletes ask you to type a word. Qikink's cost, its SKUs and the partners' rates are shown locked; only what's yours to change is open. Cancelled orders no longer count as orders; cancelled and refunds are counted apart.
- All five shirts are made at the print partner in every size (XS to 2XL), each with its own code, so a paid order goes straight to print once the partner's live account is switched on.
- Prices: the rule is now the print partner's cost plus ₹500, rounded up to the next ₹10, and for now every shirt sells at a fixed ₹1,170 (which beats the rule; the admin can still set its own).
- Every back now prints at 13.5 x 18 in, the largest the print partner prints at the art's shape (it turns away 15 x 20). The 3D, the true-size view, the try-on, the hover cards and every studio and turntable picture show it at that size.
- Checkout checks a Maharashtra pin code is really in Maharashtra. Where the shop sends is one setting now (still anywhere in india).
- Prices, which shirts are on sale and whether the shop is taking orders now come from the shop's own settings, so they can change without a new version of the site; checkout always charges the price the server works out, and the buttons, bag and checkout show that same price. A shirt can be marked sold out: its buy button says so. An order's page and receipt list every refund on it with its reference, and the receipt shows what was paid after refunds. Refunds go at normal speed (free; banks show them in 5–7 working days).
- Orders, sign-ins and the order marks are kept in a Postgres database on Neon (Singapore) instead of Upstash; the privacy policy says so.
- The label is called sahn now: in the header, the footer, every page's title and share card, the words on the photos you save from the 3D and the try-on, and their file names. The site's own addresses (in search results and share cards) follow its domain, sahn.in once it points here. Lineup 01 is still lineup 01 · fred again.. india · fan made.
- Nothing on the site says soon: no buy button, contact or policy link shows until it's real.
- His hair and beard: the hairline is a man's now, a soft curve across the forehead set back a touch at the temples, its last few millimetres fine short hairs, and the quiff grows full right from it instead of sitting on a band of short hair like a cap. The beard is kept trimmed and shaped: one even length all over with skin just showing through, a clean cheek line running diagonally from above the corner of the mouth back to the sideburn, a moustache that curves down into it, sideburns that fade up into the faded sides, and a neat neck line a finger's width under the jaw, the neck below it shaved. At the back the hair ends cleanly above the fade instead of in a ragged rim.
- His and her hands hang relaxed now, not like a shop mannequin's: the fingers close up side by side and curl a little, more toward the little finger, and the thumb comes in to lie along the index finger.
- Worn, the person moves more like someone standing at a show: deeper breaths that lift the shoulders, the weight drifting from foot to foot, the arms swinging a little, and the hands rocking and easing in and out at the wrist.
- Worn opens in the studio light; show and window are a click away.
- 05 actual life: the note at the coffee stall reads filter coffee's still on.
- Her hairline is hair now, not the edge of a cap: short fine strands come out of the skin all along her forehead and temples and are combed off to each side from a fine middle parting, and the longer hair ends under them instead of in a line across the forehead.
- Worn, the view takes in the whole face now, from just above the head to the middle of the thighs, instead of cutting at the eyes and showing the legs.
- The show is the night in the round at Alexandra Palace: a canopy of sheer white cloth hung in rings of swags over the crowd, glowing in the haze, the long low stage in the middle with its desk lamps, people on the stage behind the decks, search lights, beams coming down through the cloth, and the crowd all round you.
- At the show the canopy breathes: every swag rises and falls on its line in a slow wave that runs round the hall and out from the decks, and the cloth swings and fills as it goes. Held still for anyone who asks for less motion.
- At the show the crowd is drawn soft, as a fast portrait lens would see them behind you; the hall, the cloth, the lamps and the stage stay sharp.
- The light is called show, not the show.
- New title lettering on all four shirts (again.., i am a party, mumbai, bengaluru): a marker hand set straight, every letter the same size on one level line, no tilt. The notes and dates stay as they were.
- Up close is now on the table: it zooms in closer than before, out just far enough for the whole tee, sleeves and all, and pans only as far as the zoom allows.
- The print stays at full quality at every zoom, and renders sharper whenever the machine has room for it.
- Every load says something different: a word in hand picked at random from twenty or more for that kind of load (dressing it.., lights down.., closer.., swapping shirts.., in the darkroom.., tape out.. and the rest), never the same twice in a row. No more breathing in..
- The actual size button is called artwork.

### Fixed
- Admin health only raises amber or red for what really stops or slows an order, each with what to do about it; the payment backup waiting for its first payment and an order sync that hasn't run yet stay grey.
- The visits counted before the new visitor log are back in the admin, page by page, with their bag and checkout steps. Orders sync again whenever the admin is opened and GitHub has skipped its 3-hourly run.
- Tighter security headers on every page (HTTPS only, no framing by other sites, the camera for the try-on only), the admin never cached or indexed, and the visitor code sent in a header instead of the address.
- A shirt is for sale only when a paid order for it can really go to print: never while the print partner is on its test setup with real payments on, and the shirt codes set in the admin are the ones a paid order is sent with (before, only the ones in the code were).
- A real payment is never sent to the print partner's sandbox or without the shirt's code: the order waits, paid, and goes to print on the next try once the partner's live keys and codes are in.
- 3D views: the place around the person is drawn only where the person doesn't cover it: the same picture, less work every frame.
- 3D views: the full-size back print loads when you zoom in or open on the table (looks the same until then); only the last three shirts' prints and the last two places' sharp pictures stay in graphics memory.
- 3D views: where the graphics card's timing can't be read and frames keep arriving late, steady motion runs at an even 30 instead of an uneven 40.
- An order's page names the courier the way the print partner gives it, and shows no tracking link until there is an airway bill (before dispatch the partner's link is empty).
- Test orders to the print partner's sandbox now ask for each shirt's own blank: black or off white, and its 2XL by the name the partner uses.
- The privacy policy says how the site counts its own visits: the page, where a visit came from, the device and the region, with no cookie, no address kept and a code that changes daily; do not track and global privacy control turn it off.
- Every price on the site (the shirt cards, the shirt pages, the shop, help, the facts, share descriptions) is the one checkout charges, read from the shop itself, so the two never disagree. Each shirt's name, its short description and the order the shirts come in follow the shop's catalog too, the same on every page, and a shirt taken off sale leaves every page.
- The site's own address is www.sahn.in everywhere: search results, share cards, the sitemap and the links in order emails no longer point at the old vercel.app address. sahn.in on its own takes you there.
- Fingernails sit on every fingertip again (the thumb's was missing, some were a few stray spots).
- His tee sits better at the arms: his arms hang a little more open, as his build makes them, so the sleeves no longer bunch up into folds at the armpits or pull tight across the back of the arm.
- The 3D view is much lighter on a laptop: the slow motion on its own (breathing, the breeze, the slow turn) is drawn at an even 30 frames a second, and only what you do yourself (turning, zooming) at 60 or more; it draws past the screen's own sharpness only when the graphics card has most of its time to spare, so the rest of the computer stays smooth.
- No more spikes of cloth: a few points of the tee that the simulation had thrown out (a spike off his sleeve, torn-off flaps when sitting or with hands up) sit back in the cloth, in the shop and in fit mode.
- The tee's inside is plain cotton again, as in the renders, instead of carrying the prints; and the 3D draws the outside of the tee first, so what it covers (its inside, the body under it) is never lit only to be hidden: about a fifth less work for the graphics card every frame.
- On a graphics card that can't draw 60 frames a second, the breeze, the breathing and the slow turn run at an even 30 instead of a ragged 15 to 40, leaving the card time for the rest of the page; turning it by hand still gets every frame.
- The word and the breathing dot shown while a view gets ready sit on a soft shade of their own, so they read on a black tee too.
- The tee shows in 3D again (worn and on its form): it had stopped being drawn at all, leaving a white space and the body hollow where the tee should be.
- The places behind the person are sharp: the studio, the window and the show are drawn as finely as the screen shows them, about four times the detail they had, and nothing is blurred on purpose any more. The studio and the window come from photographs four times as large; the show is rendered at that size. Phones get them at half size, still twice what they had.
- Switching the light (studio, window, the show) is instant and no longer stalls the page: the lights are set, not rebuilt, so nothing has to be recompiled; each place's picture is decoded off the page's thread, its light measured once, and kept, and the other places are got ready while the page is idle.
- Switching shirts shows the new shirt at once: its studio render (the tee view) or its render in the hall (worn at the show) covers the view at that angle, and the live tee takes over from exactly there and turns on. Elsewhere the last frame stays up and fades into the new one, never a dark gap. A shirt you point at is got ready before you pick it.
- The cloth is simulated on its own thread, so turning, scrolling and switching stay smooth on slower machines; the light from the place turns with the view at a tiny fraction of the cost.
- The photo renderer only loads when a photo is asked for, and the rendered frames under the 3D are dropped once it's up.
- The first switch to each shirt no longer holds the page: the print is decoded, scaled down for distance and sent to the graphics card a little at a time between frames, every pixel exactly as the artwork file has it. The shirt's render stays up until the whole print is in, so it's never shown softer or half loaded.
- Switching views (the tee, worn, on the table) no longer holds the page, the first time or after: each view's tee and person stay loaded once seen, cloth and all, and the other views are got ready while the page is idle. The table works out the tee's outline in a fraction of the time, and its wood, the leaves and each place's picture go to the graphics card a little at a time.
- The view's picture for the strip is taken without making the page wait for the graphics card.
- The site holds much less memory, which on most laptops is the graphics card's memory too: a place's picture is let go on the page once it's on the card, only the shop tee and the person stay loaded, and each place's sharp band is fetched when that place is first shown (it sharpens a moment after the place appears) instead of all of them up front.
- Pictures go to the graphics card only as fast as it takes them in, so a busy machine is never held up by a big one.

## 0.18.1 — 2026-11-25
Cleaner shoulders and collar in the try-on, and clips that open on the tee.

### Try-on
- No more flecks of the room on the shoulders beside the collar: the tops of the shoulders are always solid tee.
- The edge of you no longer leaves stray specks over the tee; your hair, face and hands still show in front.
- A recorded clip has the tee from its very first frame.

## 0.18.0 — 2026-11-25
### New
- the tee view zooms in and out like the others (− zoom +, a pinch, a double-click) and slides along the print when close.

### Fixed
- The arrows and the little pictures over the 3D view click again (a press on them was taken as the start of a drag).
- Zooming in is sharp straight away: the back print at full resolution loads in the background once the 3D is up.
- The air never stops dead: a lull drops to a soft draught, so the cloth keeps moving.
- While the 3D loads, the tee view shows the tee on its own (the studio render), not someone wearing it; it opens on the back.

## 0.17.0 — 2026-11-25
### Studio
- up close has an actual size button: the print opens as big as it is on the shirt, on the shirt's own colour, to drag around. A dashed bank card outline checks the screen's scale; − and + set it right, and it's kept for next time.
- Keys 1, 2 and 3 turn the view to the front, ¾ and the back (up close: the front and back prints) while the viewer is on screen.
- New studio stills and turntable for 02 i am a party (no mirror ball) and 03 Mumbai.

## 0.16.4 — 2026-11-25
### Shirts
- 03 Mumbai map has its new lettering: the note reads we were somewhere in here, i swear, and every arrow has its dark line back.
- New try-on textures and prints to match.

## 0.16.3 — 2026-11-25
### Shirts
- 02 i am a party has no mirror ball after all; the title sits centred again.

## 0.16.2 — 2026-11-25
### Shirts
- The mirror ball on 02 i am a party is smaller and sits right after the date, no string: bigger tiles, lit from one side, every tile its own flat tone.

## 0.16.1 — 2026-11-25
02 is i am a party now, after the Fred again.. song.

### Shirts
- The title reads i am a party, with a small mirror ball hanging beside it: a real ball of mirror tiles, rendered and cut into flat tones, a blue light glancing off one side.
- the warmest place in the city sits lower now, over the crowd, out of the sky. The nose line is can't feel my nose. don't care. Both notes have small arrows.
- New try-on textures and prints to match.

## 0.16.0 — 2026-11-25
02 is called envelops me now, after a Fred again.. song, the way Still Breathing is.

### Shirts
- Its back is lettered again over the same heat picture: envelops me / india . 12 . 2026 in the crowd's hand, the title's dark edge between the two earlier tries, the date's thinner.
- The notes: bengaluru, 16° at night and mumbai, 20° at night where they were; the warmest place in the city over the crowd; the nose stays cold with a small arrow; hands up for the drop; his first fred show.
- New try-on textures and prints to match.

## 0.15.0 — 2026-11-25
Breath belongs to the whole tour now.

### Shirts
- 02 breath (black) is drawn again for both nights: a real crowd seen from the stage through a heat camera, the heat in flat bands of colour with clean edges, the far crowd melting into a purple haze, every breath rising. No grain.
- Its back reads breath.. / india . 12 . 2026, lettered in the crowd's hand, with notes: bengaluru, 16° at night; mumbai, 20° at night; hands up since the first song; the nose stays cold.
- The tour has two shirts, the crowd and breath; Mumbai and Bengaluru each have their map.
- New try-on textures and turntable frames for breath.

## 0.14.2 — 2026-11-25
The tee hangs even on you.

### Try-on
- Stand easy and the tee sits square and level, the same on both sides: the small tilts and turns the camera can't tell from noise no longer lean it, lift one shoulder or push one side of the hem forward.
- A real lean, turn or shrug still comes through whole, with no lag.

## 0.14.1 — 2026-11-25
The tee fills out on a bigger body, the way cotton does.

### Try-on
- The tee keeps its size and its loose fit. Where your body is wider than the tee at some height, the cloth is pushed out to lie on you, only there and only as far as heavy jersey gives; on most bodies it hangs free and nothing changes.
- Past what the cloth can give it stays tight, the way a size too small would look on you.

## 0.14.0 — 2026-11-25
Record yourself in the tee.

### Try-on
- A record button next to take a photo: up to 30 seconds of you in the tee, exactly as you see it, mirror, tee and hands.
- Clips save as MP4 where the phone or browser can write it (iPhone, Android, recent Chrome), WebM otherwise.
- Photos and clips can go straight to any app through your phone's share sheet, or save to the device. Nothing leaves it until you do.

## 0.13.2 — 2026-11-25
### Studio
- The shades near the edges come and go slowly and evenly now. The bottom one only rises at the very bottom, wider and softer.

## 0.13.1 — 2026-11-25
### Studio
- Down by the bottom of the view a softer shade comes up too, so the strip of views and the counter read clearly over any light.

## 0.13.0 — 2026-11-25
### Studio
- Nothing half-ready is ever shown. Switching views, shirts or the light fades the view out, a slow breath (and after a beat, "breathing in..") holds the stage while the new one gets ready, the person, the room and all, and only then it fades back in whole. On opening, the 3D takes over from the photos only once its room is in too.
- The strip of little pictures sits in the middle at the bottom on wider screens, each one the view as it really looks: the tee on its own, the person in it, the print. Hover for its name, click to go. The counter is back in its corner.

## 0.12.3 — 2026-11-25
### Site
- From abroad, the tour shirts follow Mumbai or Bengaluru, the two gateways, by real flight time from where you are: Mumbai from the Gulf, Europe, Africa and the Americas (the most direct routes), Bengaluru from Sri Lanka, Southeast Asia and Australia.

## 0.12.2 — 2026-11-25
### Site
- The countdown and the rest of the page really do follow your show now. The first shirt on the page never asked where you are, so everyone saw the next date, Delhi NCR.

## 0.12.1 — 2026-11-25
### Site
- For the tour shirts, the page now talks about the show that's quickest for you to reach, not the one nearest on a map: by road when it's close, by air when it's far, with a little grace for the cities with two nights. From Pune that's Mumbai.

## 0.12.0 — 2026-11-25
### Studio
- The view counter is a strip of three little pictures in the corner of the stage, one per view, like a photo app's: see what each shows, tap to go.
- Up close picks between the back and the front.
- The shade near an edge is deeper and comes up more slowly, so the arrow on it reads clearly.

## 0.11.0 — 2026-11-25
### Studio
- The carousel is three views now. **The tee** opens first: the shirt alone on paper, turning slowly; drag to turn it, or pick front or back. **Worn**: someone in it at the place you pick, with front, ¾, side and back, zoom, the light and the photo. **Up close**: framed on the whole back print, or the chest print, with the cloth still moving; zoom right in and slide along it. ¾ back, flat and the art are gone.
- The arrows on the picture are drawn like the notes on the shirts: a marker arrow, small and quiet until you come near that side, then the room dims softly there and a word in hand says where it goes.
- The mouse wheel only zooms once you've put your hand on the tee, so scrolling the page never gets caught in the viewer.

## 0.10.2 — 2026-11-25
### Studio
- Turning the tee never mixes in an old design's frames again. Every file the viewer loads now has its own fingerprint in its address, so a frame or texture that changed is always fetched fresh, and the ones that didn't stay cached.

## 0.10.1 — 2026-11-25
### Studio
- No more flicker while turning the tee. The twelve rendered frames load together and swap in place, so a drag never shows an empty stage. The path-traced still no longer comes and goes over the live cloth; it only develops the photos you ask for. The last view stays up while the next one loads.
- Each device gets what runs well on it: WebGPU desktops get everything plus photos; WebGL2, phones and machines with 4 GB or less get the same live view at up to 1.5x sharpness; with no real graphics, the rendered frames.

## 0.10.0 — 2026-11-25
### Studio
- The 3D view is a carousel of six views, each locked to what it shows: worn (someone in it at the place you pick, turn and zoom), alone (the tee by itself on paper, turn it), ¾ back (the hero angle, leaning toward the pointer), flat (the back straight on), close (right in on the print, slide along it) and the art (the artwork flat, pan and zoom). The cloth keeps moving in the air in every 3D view. Arrows on the picture, or the arrow keys.

## 0.9.3 — 2026-11-25
### Shirts
- Breath is a tour shirt now, next to the crowd: 01 crowd, 02 breath, 03 the Mumbai map, 04 the Bengaluru map.

## 0.9.2 — 2026-11-25
### Shirts
- End of the line is gone from the lineup, with its prints and frames.

## 0.9.1 — 2026-11-25
### Shirts
- 01 crowd: four more notes in the same hand: a december moon / mallige in her hair / best friends since 7th std / filter coffee, still hot.

## 0.9.0 — 2026-11-25
Bengaluru's map, drawn again as a picture to wear.

### Shirts
- 03 map (off white): closer in, so the grounds are the picture. Everyone in the crowd is a small drawn person seen from above, arms up; friends hold hands in pairs and dance in rings. The halls stand up off the ground, the Green Line is a solid line with the last train in at Madavara, buses, autos and cars are jammed on Tumakuru Road outside the gate, and the village streets run down to the lake, where bengaluru and the dates sit on the water.
- Four handwritten notes: madavara. the green line ends here / everyone's on tumakuru road / we'll be somewhere in here / strangers, holding hands.
- Bigger, bolder marks everywhere: no fine dots or speckle.

## 0.8.1 — 2026-11-25
### Shirts
- 01 crowd: the two friends on the right are drawn again, both from behind, his arm round her shoulders.

## 0.8.0 — 2026-11-25
Breath and end of the line are back.

### Shirts
- 04 breath (black): the crowd through a heat camera on a cold December night, hands up, every breath rising.
- 05 end of the line (off white): the Green Line out to Madavara, its last station, where the show is.
- Both sit in the Bengaluru row next to its map, and you can turn them in the viewer and try them on.

## 0.7.1 — 2026-11-25
### Viewer
- The tee turns half as fast on its own: one slow turn in about 51 seconds.

### Fixes
- The "now" strip no longer breaks the home page when the forecast service turns the request away; it just leaves the weather out.

## 0.7.0 — 2026-11-25
Your hands and hair in front of the tee, to the pixel.

### Try-on
- Your hands, forearms, hair and face show in front of the tee with their real edges. A trained model on your device reads every pixel of the camera as hair, skin, face, clothes or background; nothing leaves the browser.
- Your own clothes never show through, and bare skin counts only along your forearms and hands.

## 0.6.0 — 2026-11-25
The studio and the living room are real places now.

### Viewer
- The studio is a real daylight photo studio, photographed all the way round: paper rolls on the wall, a tall window, an octabox and a strip softbox on their stands, folding screens.
- The window light is a real sunny flat: a curtained corner window, the sun across the floorboards, a sofa against a plaster wall, plants and a small kitchen.
- The floor stays under the person's feet as you walk round, and the windows and softboxes you see are the lights on the tee, from where they stand and as bright as they are.

## 0.5.0 — 2026-11-25
A try-on that moves like a shirt on you, and three real places to see it in.

### Try-on
- Reacts sooner: where you stand, your turn, your hips and your arms follow quick movement almost at once, and holding still stays as steady as before.
- The tee stays on your shoulders when you move fast.
- Shrug one shoulder and only that side of the tee rises; the hem stays level.
- Raise your arms and the tee rides up on that side, as on a person, and settles back as you lower them.
- Sit down and the hips stay upright.
- No gaps at the shoulders, and no shadows across your face.

### Viewer
- Three places, each its own: a white studio, a sunny living room and the show's hall. Each wraps all the way round you and lights the tee and the person from every side.
- The show is lit the way a crowd is: a warm and a cool light over the stage, a follow spot from the side, the front-of-house spots behind.
- The body is solid: a gust no longer pushes the tee through the chest.
- The person looks like one: denim jeans, eyes with a shine, relaxed hands and an easy stance.

### Shirts
- 01 crowd: the voice-note line under again.. is gone.

### Fixes
- The version at the foot of the page was stuck at 0.3.1. It now matches the release.

## 0.4.0 — 2026-11-24
Three shirts: the crowd for the whole tour, a map for each city. And a viewer you can get close to.

### Shirts
- 01 crowd (black) is now one drawing for the tour, built on the Bengaluru crowd. Bengaluru is on the left: the Green Line stopping at Madavara, rain trees, a train pulling in. Mumbai is on the right: the skyline behind the race course, the twin crowns, a crane, kites, a plane lining up. In front are people from both nights. The back reads again.. / india . 12 . 2026.
- 02 map (off white): Mumbai's race course, unchanged.
- 03 map (off white): Bengaluru's NICE Grounds from above, drawn in the Mumbai map's hand: the halls, the crowd and the stage, sound rings, the Green Line ending at Madavara beside the grounds, the NICE Road interchange, the lake. It replaces end of the line and breath.
- The picker gets a "the tour" row for the shirt that belongs to no one city.
- Flat inks everywhere: no grain in any art.

### Viewer
- Zoom up to 5x with the wheel, a pinch, a double-click or the +/− buttons, and keep turning the shirt while zoomed. Zoomed in, the print swaps to a full-resolution copy, fetched only then.
- Livelier, lighter cloth: a quicker sway, a little more breeze, and the hem keeps its carry when you let go. Edges stay smooth when you drag hard.
- The chest no longer shows through the shirt. The display form is a hull, and the meshes are lighter.
- The small notches at the hem and the sleeve ends are closed.
- Scrolling no longer stutters: the 3D pauses while the page scrolls and is capped at 60 fps at rest.
- Smaller print files with sharper lines (area-averaged downsizing).

## 0.3.1 — 2026-11-24
Runs on any laptop. The viewer decides per device how much to do, and the shirt is on screen at once.

- Photo first: the path-traced frame shows the moment the page opens and can be turned; the 3D takes over when it is ready, at the same angle, and only loads once the viewer is near the screen.
- Three levels, picked per device before any 3D code downloads: path tracing on a real GPU, the live view alone on a modest one (resting on the traced frames at each 30°), and the traced frames only where there is no real GPU, 2 GB of memory or Data Saver is on.
- The tracer times itself: too slow, and it first traces fewer pixels, then hands over to the frames.
- Dragging drops resolution when frames run slow and goes back to full sharpness at rest. Nothing runs while the viewer is off screen.
- Turntable frames are WebP: 29 MB down to 1.5 MB for all four shirts (about 20 KB a frame). render.yml now writes WebP.
- Mahalakshmi's two dots get room on 04.

## 0.3.0 — 2026-11-24
Bengaluru gets its two shirts. Everything is for sale, one colour per shirt, a cleaner print, and the tee on bodies like the people buying it.

### Shirts
- Bengaluru, drawn from scratch:
  - 03 breath (black): the crowd as a heat camera on the stage sees it on a December night, hands up, breath rising into the cold. Rendered from our own five Indian bodies (460 people), with a thermal readout, ಉಸಿರು / breath.
  - 04 end of the line (off white): the Green Line northbound from Majestic to Madavara, its last station and the show's, set in Kannada and English. Bengaluru is the last city of the tour. Mahalakshmi carries two blue dots for Mumbai's ground.
- The picker groups the shirts by city; the heading follows the shirt (again.. mumbai / again.. bengaluru).
- One colour each: 01 crowd is black, 02 map is off white. No colour picker.
- Front: "again.." in four scripts (again.. / फिर से.. / पुन्हा.. / ಮತ್ತೆ..) on the left chest at chest height. No name, no date.
- Back: the art fills the largest print the blank allows (15 x 20 in at 3:4).
- Copy says what it is: made to order, for sale, sent anywhere in India.

### Viewer
- No grain, ever: the path tracer works out of sight and the denoised frame fades in over the real-time view. No sample counters.
- Edge-avoiding à-trous denoiser (normal, depth and luminance guided, albedo demodulated), so folds and print edges stay sharp at 40 samples.
- Photo mode: story (1080 x 1920) or post (1080 x 1350), clean or film, with a caption. 64 samples + denoise, seconds instead of minutes. Save or share.
- Lights cut to three that look real: studio, window, the show (dark room, cool stage wash, one warm spot, a dim front-of-house fill). Overcast, tube light and phone flash are gone.
- The shop tee hangs on a smooth ghost form, so the empty tee shows no chest shape.
- Fit mode: say man or woman, height and weight, pick a skin tone; the tee is shown in your size on the nearest of five simulated Indian bodies, standing, hands up or sitting, with plain words for how it fits (room round the chest, where the hem falls, how far it rides up).
- Fallback frames are re-rendered from the ghost-form tee. With no 3D at all, the page shows them instead of an error, drag to turn.
- Bigger tap targets for the small text buttons on phones.
- The shop camera steps back a little so the collar has room.

### Page
- A live "now" strip that writes itself: days to the next show, the sky over it right now, the sunset, the show-night forecast once it's in range. Public forecast for three fixed places; nothing about the visitor leaves the browser.

### Pipeline
- `body.py` builds five Indian bodies from height and chest (m163, m170, m177, f155, f162); chest is measured on the connected torso loop.
- `pattern.py` grades every size from the chart; the atlas is neck-anchored so the print sits at the same place on every size.
- `build.py` sews any size onto any body and moves it through standing, hands up and sitting (stool collider); `FORM=1` swaps the torso for the ghost form.
- `export.py` bakes cloth AO into the vertices, exports tee + body per pose, `fit.json` measures and `proxy.glb`.
- `.github/workflows/fit.yml` runs all 15 body-size sims plus the ghost form in parallel and publishes them to `public/tee/fit/`.
- `render.yml` renders fallback frames from the published ghost-form tee (`GLB=` mode in `render.py`).
- `export.py` uses plain Catmull-Clark (the limit-surface evaluator needed ~3 GB and killed CI runners) and measures the body on frame 1 (it was measured on the saved sitting frame, which shifted every waistband reading by the sit drop; published numbers corrected).
- `art/make_line.py`, `art/make_breath.py` + `art/breath_post.py` generate the Bengaluru backs; `fonts/` holds Bricolage Grotesque and Noto Sans Kannada for them.

## 0.2.0 — 2026-11-24
Lineup 01 is now two shirts, and the viewer path-traces in the browser.

### Site
- Rebuilt on Next.js. Its own look: after-dark palette, the print's blue as the only colour, Bricolage Grotesque, ruled labels and one giant word.
- Two designs: 01 crowd (lines) and 02 map (race course), each in black and off white.
- Real-time view on three.js WebGPURenderer (WebGL2 fallback built in).
- WebGPU path tracer: when you let go, the exact view is traced with the same cotton, ink, sweep and softboxes as the Cycles renders. Any angle, not just the 12 pre-rendered ones. Calibrated against the Cycles frames: chest patches match within 1-2 sRGB levels on black and off white.
- Fixed product camera (85 mm, f/5.6). The lens control is gone, so the collar never changes shape; the loupe crops and re-renders up to 12x instead.
- Removed supplier, print method, print-area and render-engine details from the page. Kept what a buyer needs: cloth, fit, sizes in cm, care, the fan-made note.
- Live countdown to the next show.

### Pipeline
- webtex.py writes maps per design: color-<design>-<tee>.jpg, orm-<design>-<tee>.png.

## 0.1.2 — 2026-11-24
- Site hosted on Vercel; every push that touches `public/` redeploys, render-farm commits included. Pipeline-only commits skip the deploy.

## 0.1.1 — 2026-11-24
- Turntable frames for both colourways rendered on the GitHub Actions render farm (24 frames, 64 spp).
- Real-time light rig calibrated against the Cycles frames, so the switch between them is close to invisible.

## 0.1.0 — 2026-11-24
First cut of the Still Breathing site and the garment pipeline.

### Site
- Product page for lineup 01 (fred again.., Mumbai tee), black and Off White.
- Real-time three.js studio: drag to turn, lens 24-200 mm with dolly, exposure, key light colour temperature and angle, fill ratio, rim light, knit detail, four backdrop papers.
- Path-traced Cycles frames take over whenever the view lands on a rendered angle at the reference light; falls back to the frames alone when WebGL is missing.
- Size chart XS-2XL, tech flat drawn from the real pattern, fit facts on the simulated body, print and cloth facts.

### Pipeline
- M pattern from the maker's published chest, length and shoulder; unpublished values are marked as estimates.
- Cloth simulation in Blender 5.3 on a 170 cm, 94 cm chest Indian male body (MakeHuman via MPFB).
- 240 GSM jersey settings, two-layer hems and rib collar, stitch and rib relief map, real single-jersey knit map.
- Print halos knocked out of the print files; ink without the cotton sheen; Khronos PBR Neutral view transform.
