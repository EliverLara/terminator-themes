import { readFile, writeFile, __dirname, unlink } from './utils'
import svg_to_png from 'svg-to-png'
import replaceall from 'replaceall'
import capitalize from 'string-capitalize'
import setColors from './svg-template'


let themes = [];
export const createNewThemesImgs = async newThemes => {
    themes = await readFile('../themes.json')
    themes = JSON.parse(themes).themes
    newThemes = newThemes.map(item => item.split('.')[0])
    let targets = themes.filter(item => newThemes.includes(item.name))

    for(let theme of targets) {
        theme.palette = theme.palette.split(":")
        await makeImg(setColors(theme), theme.name)
    }
}

const makeImg = async (xml, fileName) => {
    fileName = `${changeSpaces(fileName)}.svg`
    try {
        await writeFile(fileName, xml)
        await svg_to_png.convert(`${__dirname}/${fileName}`, "../images")   
        await unlink(fileName)
    }catch(err) {
        console.log(err)
    }
}

export const createMd = async() => {
    let darkThemesMd = buildThemesMd(themes.filter(item => item.type == 'dark'))
    let lightThemesMd = buildThemesMd(themes.filter(item => item.type == 'light'))
    let mdStr = `# Themes\n\n## Dark background\n\n${replaceall(",","",darkThemesMd.join())}\n\n## Light background\n\n${replaceall(",","",lightThemesMd.join())}
    `
    try {
        await writeFile('../themes.md', mdStr)
    }catch(err) {
        console.log(err)
    }
}

const buildThemesMd = (themes) => {
    return themes.map((theme, index) => {
        let delimiter = ++index%2 == 0 ? "\n" : "| "

        let url = `images/${changeSpaces(theme.name)}.png`
        let displayName =  capitalize(theme.name)
      
        return index == 3 ? 
        `:---------------------------------------------:|:----------------------------------------------:\n**${displayName}**![${displayName}](${url}) ${delimiter}`:  
        `**${displayName}**![${displayName}](${url}) ${delimiter}`
    })
}

const changeSpaces = (str) => replaceall(" ", "-", str)