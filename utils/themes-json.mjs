import { readFile, readdir, writeFile } from './utils.mjs'
import Color from 'color'

export default async() => {
    let schemes = await readdir('../schemes')

    let themes =  await Promise.all(schemes.map(async item => await createJson(item)))
    themes = themes.sort((a,b) => a.name.localeCompare(b.name))
    themes = themes.map( theme => {
        theme.type  = Color(theme.background_color).isDark() ?  "dark" : "light"
        return theme     
    })

    await writeFile('../themes.json', JSON.stringify( { themes }, null, 2));
}

const createJson = async file => {
    let data = await readFile(`../schemes/${file}`, 'utf-8') 
    let json = data.trim().trim()
        .split("\n")
        .slice(1)
        .map(line => line.split("="))
        .reduce((config, line) => {
            line[0] = line[0].trim();
            line[1] = line[1].trim().replace(/^"(.*)"$/, '$1');
            config['name'] = file.split('.')[0];
            config[line[0]] = line[1];
            return config;
        }, {});
    return json
}