-- PostgreSQL schema for Domovi (app tables only)
-- Auth tables are created by Django migrations (auth, admin, contenttypes, sessions).

CREATE TABLE klijent (
  id SERIAL PRIMARY KEY,
  naziv TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE dom (
  id SERIAL PRIMARY KEY,
  klijent_id INT REFERENCES klijent(id) ON DELETE CASCADE,
  naziv TEXT NOT NULL,
  kapacitet INT NOT NULL DEFAULT 0 CHECK (kapacitet >= 0),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (klijent_id, naziv)
);

CREATE TABLE zaposlenik (
  id SERIAL PRIMARY KEY,
  dom_id INT NOT NULL REFERENCES dom(id) ON DELETE CASCADE,
  ime_prezime TEXT NOT NULL,
  pozicija TEXT NOT NULL,
  bruto NUMERIC(12,2) NOT NULL CHECK (bruto >= 0),
  neto NUMERIC(12,2) NOT NULL CHECK (neto >= 0),
  datum_ugovora DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE profil (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  dom_id INT NOT NULL REFERENCES dom(id) ON DELETE CASCADE,
  zaposlenik_id INT UNIQUE REFERENCES zaposlenik(id) ON DELETE SET NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','upravitelj','zaposlenik')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE profil_upravljani_domovi (
  id SERIAL PRIMARY KEY,
  profil_id INT NOT NULL REFERENCES profil(id) ON DELETE CASCADE,
  dom_id INT NOT NULL REFERENCES dom(id) ON DELETE CASCADE,
  UNIQUE (profil_id, dom_id)
);

CREATE TABLE korisnik (
  id SERIAL PRIMARY KEY,
  dom_id INT NOT NULL REFERENCES dom(id) ON DELETE CASCADE,
  ime_prezime TEXT NOT NULL,
  datum_rodenja DATE NOT NULL,
  oib TEXT NOT NULL,
  mbo TEXT NOT NULL,
  soba TEXT NOT NULL,
  datum_dolaska DATE NOT NULL,
  iznos NUMERIC(12,2) NOT NULL CHECK (iznos >= 0),
  mjesecna_clanarina NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (mjesecna_clanarina >= 0),
  kontakt_obitelji TEXT NOT NULL,
  kontakt_obitelji_telefon TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE korisnik_uplata (
  id SERIAL PRIMARY KEY,
  korisnik_id INT NOT NULL REFERENCES korisnik(id) ON DELETE CASCADE,
  godina SMALLINT NOT NULL CHECK (godina >= 2000),
  mjesec SMALLINT NOT NULL CHECK (mjesec BETWEEN 1 AND 12),
  iznos NUMERIC(12,2) NOT NULL CHECK (iznos > 0),
  datum_potvrde TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (korisnik_id, godina, mjesec)
);

CREATE TABLE smjena (
  id SERIAL PRIMARY KEY,
  zaposlenik_id INT NOT NULL REFERENCES zaposlenik(id) ON DELETE CASCADE,
  datum DATE NOT NULL,
  tip_smjene TEXT NOT NULL CHECK (tip_smjene IN ('jutarnja','popodnevna','nocna','slobodno')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (zaposlenik_id, datum)
);

CREATE TABLE investicija (
  id SERIAL PRIMARY KEY,
  dom_id INT NOT NULL REFERENCES dom(id) ON DELETE CASCADE,
  naziv TEXT NOT NULL,
  iznos NUMERIC(12,2) NOT NULL CHECK (iznos > 0),
  datum DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE trosak (
  id SERIAL PRIMARY KEY,
  dom_id INT NOT NULL REFERENCES dom(id) ON DELETE CASCADE,
  naziv TEXT NOT NULL,
  kategorija TEXT NOT NULL CHECK (kategorija IN ('kuhinja','popravci','opcenito')),
  iznos NUMERIC(12,2) NOT NULL CHECK (iznos > 0),
  trgovina TEXT,
  meso TEXT,
  datum DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE rezija (
  id SERIAL PRIMARY KEY,
  dom_id INT NOT NULL REFERENCES dom(id) ON DELETE CASCADE,
  naziv TEXT NOT NULL,
  iznos NUMERIC(12,2) NOT NULL CHECK (iznos > 0),
  interval TEXT NOT NULL CHECK (interval IN ('bez_intervala','mjesecno','kvartalno','polugodisnje','godisnje')),
  datum_pocetka DATE NOT NULL,
  datum_zavrsetka DATE,
  aktivna BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CHECK (datum_zavrsetka IS NULL OR datum_zavrsetka >= datum_pocetka)
);

CREATE INDEX korisnik_dom_ime_idx ON korisnik(dom_id, ime_prezime);
CREATE INDEX korisnik_dom_oib_idx ON korisnik(dom_id, oib);
CREATE INDEX korisnik_uplata_period_idx ON korisnik_uplata(korisnik_id, godina, mjesec);
CREATE INDEX investicija_dom_datum_idx ON investicija(dom_id, datum);
CREATE INDEX trosak_dom_datum_idx ON trosak(dom_id, datum);
CREATE INDEX trosak_dom_kategorija_idx ON trosak(dom_id, kategorija);
CREATE INDEX rezija_dom_aktivna_idx ON rezija(dom_id, aktivna);
CREATE INDEX zaposlenik_dom_idx ON zaposlenik(dom_id);
