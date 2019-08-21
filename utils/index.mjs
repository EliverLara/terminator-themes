import execa from 'execa'
import createThemesJsonFile from './themes-json.mjs'
import { createNewThemesImgs, createMd } from './themes-extras.mjs'

const main = async() => {
    try {
        await createThemesJsonFile()
        let newThemes = await execa.stdout('git', [ '-C', '../schemes', 'ls-files', '--others', '--exclude-standard'])
        await createNewThemesImgs(newThemes.split('\n'))
        await createMd()
    }catch(err) {
        console.log(err)
    }
} 

main()