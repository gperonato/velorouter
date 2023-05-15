# Velorouter

This repository contains a web-based route planner for bike paths in Switzerland based on the following datasets:

 - [Veloland Schweiz](https://data.geo.admin.ch/browser/index.html#/collections/ch.astra.veloland") (v. 4/26/2023) provided by Switzerland's Federal Roads Office (FEDRO) and comprizing "the national, regional and local cycling routes in Switzerland and Liechtenstein";
 
 - [swissTLMRegio](https://www.swisstopo.admin.ch/en/geodata/landscape/tlmregio.html) (v. 2022) provided by Switzerland's Federal Office of Topography (swisstopo), specifically the layer of named locations.


## Use

The datasets need to be first downloaded into the `data` directory.

```
cd data
./get_data.sh
```

Recommended use for running the web app is with `docker-compose`:

```
docker-compose up
```

By default the web app runs on:

[http://localhost:8050](http://localhost:8050)

## Web app

See a running web app on [velorouter.ch](www.velorouter.ch).

## Contributors (a-z):

- [Giuseppe Peronato](https://www.giuseppeperonato.com)

## Terms of use

The app is released under the AGPLv3 license (see below). The terms of use specific to each source dataset also apply. 

### License

VeloRouter: a route planner for Swiss bike routes.

Copyright (c) 2023 Giuseppe Peronato

This file is part of VeloRouter.

VeloRouter is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License version 3 as
published by the Free Software Foundation.

VeloRouter is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License version 3 for more details.

You should have received a copy of the GNU Affero General Public License version 3 along with VeloRouter. If not, see <http://www.gnu.org/licenses/>